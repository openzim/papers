"""OPDS-backed Littérature jeunesse libre (LJL) discovery.

LJL publishes an index of its catalogue and filters as an OPDS Atom feed ready for
export. Each filter lists all the books in the catalogue that match that specific
criteria. Every entry is self-contained: it carries the title, description, author,
language, thumbnail, source page and ready-made download links for the supported
formats (EPUB and PDF). So a `WorkRef` here already holds everything the metadata
port needs - no per-book fetch
"""

# ruff: noqa: S314

import re
import unicodedata
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import asdict, dataclass
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

from zimscraperlib.i18n import get_language_or_none

from papers2zim.constants import logger
from papers2zim.core.categories import normalize_category
from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.fulltext import html_text
from papers2zim.core.models import Format
from papers2zim.core.ports import CatalogFilters, CatalogPort, WorkRef
from papers2zim.core.utils import critical_error, normalize
from papers2zim.sources.litteraturejeunesselibre.categories import (
    category_resolver,
)

BASE_URL = "https://litterature-jeunesse-libre.fr/bbs/opds"
LJL_SOURCE = "litteraturejeunesselibre"
SUPPORTED_FORMATS = frozenset({"epub", "pdf"})
EPUB_MEDIA_TYPE = "application/epub+zip"
PDF_MEDIA_TYPE = "application/pdf"

FORMAT_BY_MEDIA_TYPE = {
    EPUB_MEDIA_TYPE: "epub",
    PDF_MEDIA_TYPE: "pdf",
}

ACQUISITION_REL = "http://opds-spec.org/acquisition"
COVER_RELS = (
    "http://opds-spec.org/image/thumbnail",
    "http://opds-spec.org/image",
)

NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "opds": "http://opds-spec.org/2010/catalog",
    "dcterms": "http://purl.org/dc/terms/",
}

NAVIGATION_LINK_TYPE = "atom:link[@type='application/atom+xml;profile=opds-catalog']"

UUID_RE = re.compile(
    r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}",
    re.IGNORECASE,
)

# Calibre OPDS feeds prefix the HTML description with the book's tags.
TAGS_PREFIX_RE = re.compile(r"^\s*TAGS\s*:[^<]*(?=<)", re.IGNORECASE)

# OPDS feeds paginate through rel="next", and a malformed feed
# could otherwise loop forever. This is far above any realistic catalogue page
# count for a single filter.
MAX_FEED_PAGES = 1000


def _normalize_whitespace(value: str | None) -> str | None:
    """Collapse whitespace in value, returning None when it is blank."""
    if value is None:
        return None
    return " ".join(value.split()) or None


def _normalize_author(value: str | None) -> str:
    """Order- and accent-independent key for an author name."""
    decomposed = unicodedata.normalize("NFKD", value or "")
    text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(sorted(re.findall(r"\w+", text.casefold())))


def parse_uuid(value: str) -> str | None:
    """Return the canonical UUID of a bare UUID string, or None."""
    text = value.strip()
    return text.casefold() if UUID_RE.fullmatch(text) else None


def _parse_id(value: str) -> str:
    """Return the canonical UUID of a bare UUID string, or None."""
    return re.sub(
        r"^(urn:uuid:)+",
        "",
        value.strip().casefold(),
        flags=re.IGNORECASE,
    )


def _element_texts(entry: ET.Element, path: str) -> list[str]:
    """Whitespace-collapsed text of every child matching path, skipping empty values."""
    texts = (
        _normalize_whitespace("".join(element.itertext()))
        for element in entry.findall(path, NAMESPACES)
    )
    return [text for text in texts if text]


def _element_text(entry: ET.Element, path: str) -> str | None:
    """Whitespace-collapsed text of the first child matching path."""
    texts = _element_texts(entry, path)
    return texts[0] if texts else None


def normalize_language(code: str | None) -> str | None:
    """LJL uses ISO 639-2 codes ("fra") while the pipeline uses 2-letter codes."""
    if not code or not (key := code.strip().casefold()):
        return None
    lang = get_language_or_none(key)
    return lang.iso_639_1 if lang and lang.iso_639_1 else key


def _entry_languages(entry: ET.Element) -> list[str]:
    """Normalized, de-duplicated language codes advertised by an entry."""
    languages: list[str] = []
    for value in _element_texts(entry, "dcterms:language"):
        code = normalize_language(value)
        if code and code not in languages:
            languages.append(code)
    return languages


def _description(entry: ET.Element) -> str | None:
    """Plain-text description without Calibre's redundant ``TAGS:`` line."""
    value = _element_text(entry, "atom:content")
    if not value:
        return None
    value = TAGS_PREFIX_RE.sub("", value, count=1)
    return html_text(value) or None


def _next_page_url(root: ET.Element, feed_url: str) -> str | None:
    """Resolve the rel="next" pagination link of a feed, if any."""
    for link in root.findall("atom:link", NAMESPACES):
        if link.get("rel") != "next":
            continue
        href = (link.get("href") or "").strip()
        if href:
            return urljoin(feed_url, href)
    return None


def _link_url(entry: ET.Element, rels: Sequence[str], base_url: str) -> str | None:
    """Resolve the first usable link, trying rels in order."""
    for rel in rels:
        for link in entry.findall("atom:link", NAMESPACES):
            href = (link.get("href") or "").strip()
            if link.get("rel") == rel and href:
                return urljoin(base_url, href)
    return None


def acquisition_urls(
    entry: ET.Element, base_url: str, formats_by_media_type: dict[str, str]
) -> list[Format]:
    """URLs of the acquisition link in a format the pipeline can handle."""
    formats: list[Format] = []
    for link in entry.findall("atom:link", NAMESPACES):
        rel = link.get("rel") or ""
        if rel != ACQUISITION_REL:
            continue
        media_type = (link.get("type") or "").split(";", 1)[0].strip().lower()
        href = (link.get("href") or "").strip()
        try:
            size = int((link.get("length") or "").strip())
        except ValueError:
            size = None
        if media_type in formats_by_media_type and href:
            formats.append(
                Format(
                    name=formats_by_media_type[media_type],
                    media_type=media_type,
                    url=urljoin(base_url, href),
                    size=size,
                )
            )
    return formats


def _entry_categories(entry: ET.Element) -> list[str]:
    """Collapse an entry's category terms into broad collections."""
    terms: list[str] = []
    for category in entry.findall("atom:category", NAMESPACES):
        term = _normalize_whitespace(category.get("term"))
        if term and term not in terms:
            terms.append(term)
    return category_resolver.collections_for(terms)


@dataclass(frozen=True, slots=True)
class LJLCatalogBook:
    """A book card from the Littérature jeunesse libre listing."""

    id: str
    title: str
    formats: list[Format]
    categories: list[str]
    languages: list[str]
    authors: list[str]
    cover_url: str | None = None
    description: str | None = None

    def to_ref(self) -> WorkRef:
        extra = asdict(self)
        extra.pop("id")
        extra["formats"] = list(self.formats)
        return WorkRef(
            id=self.id,
            source=LJL_SOURCE,
            extra=extra,
        )


@dataclass(frozen=True, slots=True)
class Page:
    """A sub-page of the catalogue, as listed by its navigation feed."""

    id: str
    url: str


class LitteratureJeunesseLibreCatalog(CatalogPort):
    """Discover Littérature jeunesse libre books from OPDS feeds."""

    def __init__(
        self,
        engine: DownloadEngine,
        base_url: str = BASE_URL,
        **_: object,
    ):
        self._engine = engine
        self._base_url = base_url.rstrip("/")

    def discover(self, filters: CatalogFilters) -> Iterable[WorkRef]:
        requested_formats = set(filters.formats or SUPPORTED_FORMATS)
        if not requested_formats.intersection(SUPPORTED_FORMATS):
            logger.info(
                "Littérature jeunesse libre only offers EPUB and PDF; no requested "
                "format can be downloaded"
            )
            return []

        requested_categories = {
            normalize_category(category)
            for category in filters.options.get("categories") or []
        }
        if requested_categories:
            available = {normalize_category(name) for name in category_resolver.order}
            unknown = sorted(requested_categories - available)
            if unknown:
                critical_error(
                    "No Littérature jeunesse libre category matches "
                    f"{', '.join(unknown)!r}. Available categories: "
                    f"{', '.join(self.list_categories())}. "
                    "Use --list-ljl-categories to browse them."
                )

        pages = self._select_filter_pages(filters)
        # The same book is listed once per category/series page it belongs to, so
        # keep only its first occurrence.
        books_by_id: dict[str, LJLCatalogBook] = {}
        for page in pages:
            for book in self._parse_books(page):
                books_by_id.setdefault(book.id, book)
        books = list(books_by_id.values())

        if requested_categories:
            books = [
                book
                for book in books
                if requested_categories
                & {normalize_category(name) for name in book.categories}
            ]

        requested_ids = {
            parsed
            for book_id in filters.options.get("book_ids") or []
            if (parsed := parse_uuid(str(book_id))) is not None
        }
        if filters.options.get("book_ids"):
            books = [book for book in books if book.id in requested_ids]

        if not books:
            critical_error("No Littérature jeunesse libre books were discovered")

        return [book.to_ref() for book in books]

    def _select_filter_pages(self, filters: CatalogFilters) -> list[Page]:
        """
        Select the pages that correspond to the specific filter.

        LJL website filters are mutually exclusive. The available filters are
            - title: find books starting with a specific alphabet/number
            - author: find books written by a specific author
            - categories: find books belonging to a specific category
            - series: find books belonging to a particular series
        """

        if inputs := filters.options.get("series"):
            filter_kind = "series"
            pages = self._list_series()
        elif inputs := filters.options.get("authors"):
            filter_kind = "authors"
            pages = self._list_authors()
        elif inputs := filters.options.get("categories"):
            # Categories are the collapsed collections, not LJL tags, so the
            # whole title index is fetched
            return self._list_titles()
        elif inputs := filters.options.get("title"):
            filter_kind = "title prefixes"
            pages = self._list_titles()
        else:
            # No filter means the whole catalogue
            return self._list_titles()

        if filter_kind == "authors":
            requested = {_normalize_author(value) for value in inputs}
            matching = [
                page for page in pages if _normalize_author(page.id) in requested
            ]
        else:
            requested = {
                (normalize(value) or "").strip().casefold() for value in inputs
            }
            matching = [
                page
                for page in pages
                if (normalize(page.id) or "").strip().casefold() in requested
            ]

        if not matching:
            available = ", ".join(self._sorted_page_ids(pages)) or "(none)"
            critical_error(
                "No Littérature jeunesse libre "
                f"{filter_kind} matches {', '.join(inputs)!r}. "
                f"Available {filter_kind}: {available}. "
                "Use --list-ljl-* to browse them."
            )
        return matching

    def list_series(self) -> list[str]:
        """Return every series name available on LJL, sorted alphabetically."""
        return self._sorted_page_ids(self._list_series())

    def list_authors(self) -> list[str]:
        """Return every author name available on LJL, sorted alphabetically."""
        return self._sorted_page_ids(self._list_authors())

    def list_categories(self) -> list[str]:
        """Return the broad collection names used for LJL works, sorted."""
        return sorted(category_resolver.order, key=str.casefold)

    def list_titles(self) -> list[str]:
        """Return every title prefix available on LJL, sorted alphabetically."""
        return self._sorted_page_ids(self._list_titles())

    @staticmethod
    def _sorted_page_ids(pages: Iterable[Page]) -> list[str]:
        """Return distinct page ids, sorted case-insensitively."""
        return sorted({page.id for page in pages}, key=str.casefold)

    def _list_series(self) -> list[Page]:
        """List the available series pages on LJL"""
        # The series listing lists the series index sorted alphabetically.
        # Fetch those individiual pages to get the list of series on LJL
        entries = self._list_navigation_entries("/bbs/opds/series")
        series: list[Page] = []
        for entry in entries:
            series.extend(
                self._parse_navigation_feed(
                    self._engine.fetch_bytes(entry.url).decode("utf-8"),
                    self._base_url,
                )
            )
        return series

    def _list_authors(self) -> list[Page]:
        """List the available author pages on LJL"""
        # The authors's listing lists the authors index sorted alphabetically.
        # Fetch those individiual pages to get the list of authors on LJL
        entries = self._list_navigation_entries("/bbs/opds/author")
        authors: list[Page] = []
        for entry in entries:
            authors.extend(
                self._parse_navigation_feed(
                    self._engine.fetch_bytes(entry.url).decode("utf-8"),
                    self._base_url,
                )
            )
        return authors

    def _list_titles(self) -> list[Page]:
        """List the available title pages on LJL"""
        return self._list_navigation_entries("/bbs/opds/books")

    def _list_navigation_entries(self, entry_id: str) -> list[Page]:
        """Fetch the index linked from the home entry whose id is ``entry_id``.

        The home feed advertises every browseable index (series, tags, all books,
        ...) as an ``<entry>`` with a stable ``<id>`` and a single navigation link.
        ``entry_id`` selects the entry; its navigation link is then requested and
        parsed into the pages it lists.
        """
        data = self._engine.fetch_bytes(self._base_url).decode("utf-8")
        root = ET.fromstring(data)

        for entry in root.findall("atom:entry", NAMESPACES):
            if _element_text(entry, "atom:id") != entry_id:
                continue

            navigation = entry.find(NAVIGATION_LINK_TYPE, NAMESPACES)
            href = (navigation.get("href") if navigation is not None else None) or ""
            href = href.strip()
            if not href:
                return []

            navigation_url = urljoin(self._base_url, href)
            feed = self._engine.fetch_bytes(navigation_url).decode("utf-8")
            return self._parse_navigation_feed(feed, self._base_url)

        return []

    def _iter_feed(self, xml: str, feed_url: str) -> Iterator[tuple[ET.Element, str]]:
        """Yield each page of an OPDS feed, following ``rel="next"`` links."""
        seen = {feed_url}
        current_url, data = feed_url, xml

        while True:
            root = ET.fromstring(data)
            yield root, current_url

            next_url = _next_page_url(root, current_url)
            if next_url is None:
                return
            if next_url in seen:
                logger.warning(f"Pagination loop detected at {next_url}; stopping")
                return
            if len(seen) >= MAX_FEED_PAGES:
                logger.warning(
                    f"Stopped paginating {feed_url} after {MAX_FEED_PAGES} pages"
                )
                return

            seen.add(next_url)
            current_url = next_url
            data = self._engine.fetch_bytes(next_url).decode("utf-8")

    def _parse_navigation_feed(
        self, xml: str, feed_url: str | None = None
    ) -> list[Page]:
        """Parse a navigation feed and every page linked by ``rel="next"``."""
        feed_url = feed_url or self._base_url
        pages: list[Page] = []

        for root, page_url in self._iter_feed(xml, feed_url):
            for entry in root.findall("atom:entry", NAMESPACES):
                title = _element_text(entry, "atom:title")
                if title == "All":
                    # No need to include the link for All entires since we already
                    # have the links for paginating at a more granular level e.g
                    # sorted alphabetically
                    logger.debug("Skipping nav link for fetching all entries...")
                    continue
                navigation = entry.find(NAVIGATION_LINK_TYPE, NAMESPACES)
                href = (
                    navigation.get("href") if navigation is not None else None
                ) or ""
                href = href.strip()
                if not title or not href:
                    continue

                pages.append(Page(id=title, url=urljoin(page_url, href)))

        return pages

    def _parse_books(self, page: Page) -> list[LJLCatalogBook]:
        """Parse a book listings feed and every page linked by ``rel="next"``."""
        data = self._engine.fetch_bytes(page.url).decode("utf-8")
        books: list[LJLCatalogBook] = []

        for root, feed_url in self._iter_feed(data, page.url):
            for entry in root.findall("atom:entry", NAMESPACES):
                title = _element_text(entry, "atom:title")
                feed_id = _element_text(entry, "atom:id")
                formats = acquisition_urls(entry, self._base_url, FORMAT_BY_MEDIA_TYPE)

                if feed_id is None:
                    logger.warning(f"entry at {feed_url} does not have title ")
                    continue

                if not title or not feed_id or not formats:
                    logger.warning(
                        f"entry at {feed_url} does not have title or book ID or "
                        f" formats; {title=}, {feed_id=}, {formats=}"
                    )
                    continue

                books.append(
                    LJLCatalogBook(
                        id=_parse_id(feed_id),
                        title=title,
                        formats=formats,
                        categories=_entry_categories(entry),
                        languages=_entry_languages(entry),
                        authors=_element_texts(entry, "atom:author/atom:name"),
                        cover_url=_link_url(entry, COVER_RELS, self._base_url),
                        description=_description(entry),
                    )
                )

        return books
