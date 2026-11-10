"""OPDS-backed Bibliothèque numérique romande (BNR) discovery.

BNR publishes an index of its catalogue and filters as an OPDS Atom feed ready for
export. Each filter lists all the books in the catalogue that match that specific
criteria. Every entry is self-contained: it carries the title, description, author,
language, thumbnail, source page and one ready-made download link for EPUB format. So a
`WorkRef` here already holds everything the metadata port needs - no per-book
fetch
"""

# ruff: noqa: S314

import re
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

from papers2zim.constants import logger
from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.ports import CatalogFilters, CatalogPort, WorkRef
from papers2zim.core.utils import critical_error, normalize
from papers2zim.sources.bibliothequenumeriqueromande.categories import (
    COLLECTION_ORDER,
    collection_names_for_categories,
    normalize_category,
)

BASE_URL = "https://ebooks-bnr.com/opds/index.php"
BNR_SOURCE = "bibliothequenumeriqueromande"
# BNR only publishes French-language books.
BNR_LANGUAGE = "fr"
SUPPORTED_FORMATS = frozenset({"epub"})
EPUB_MEDIA_TYPE = "application/epub+zip"

FORMAT_BY_MEDIA_TYPE = {
    EPUB_MEDIA_TYPE: "epub",
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

UUID_RE = re.compile(
    r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}",
    re.IGNORECASE,
)


def _normalize_whitespace(value: str | None) -> str | None:
    """Collapse whitespace in value, returning None when it is blank."""
    if value is None:
        return None
    return " ".join(value.split()) or None


def parse_uuid(value: str) -> str | None:
    """Return the canonical UUID of a bare UUID string, or None."""
    text = value.strip()
    return text.casefold() if UUID_RE.fullmatch(text) else None


def uuid_from_feed_id(value: str) -> str:
    """Return the canonical UUID embedded in a feed id.

    Raises:
        ValueError: when the feed id contains no UUID.
    """
    match = UUID_RE.search(value)
    if match is None:
        raise ValueError(f"No UUID found in feed id: {value!r}")
    return match.group(0).casefold()


def _element_text(entry: ET.Element, path: str) -> str | None:
    """Whitespace-collapsed text of the first child matching path."""
    element = entry.find(path, NAMESPACES)
    if element is None:
        return None
    return _normalize_whitespace("".join(element.itertext()))


def _link_url(entry: ET.Element, rels: Sequence[str], base_url: str) -> str | None:
    """Resolve the first usable link, trying rels in order."""
    for rel in rels:
        for link in entry.findall("atom:link", NAMESPACES):
            href = (link.get("href") or "").strip()
            if link.get("rel") == rel and href:
                return urljoin(base_url, href)
    return None


def _acquisition_url(entry: ET.Element, base_url: str) -> str | None:
    """URL of the first acquisition link in a format the pipeline can handle."""
    for link in entry.findall("atom:link", NAMESPACES):
        rel = link.get("rel") or ""
        if rel != ACQUISITION_REL and not rel.startswith(f"{ACQUISITION_REL}/"):
            continue
        media_type = (link.get("type") or "").split(";", 1)[0].strip().lower()
        href = (link.get("href") or "").strip()
        if media_type in FORMAT_BY_MEDIA_TYPE and href:
            return urljoin(base_url, href)
    return None


def _entry_categories(entry: ET.Element) -> list[str]:
    """Collapse an entry's category terms into broad collections."""
    terms: list[str] = []
    for category in entry.findall("atom:category", NAMESPACES):
        term = _normalize_whitespace(category.get("term"))
        if term and term not in terms:
            terms.append(term)
    return collection_names_for_categories(terms)


@dataclass(frozen=True, slots=True)
class BNRCatalogBook:
    """A book card from the Bibliothèque numérique romande listing."""

    id: str
    title: str
    source_url: str
    categories: list[str]
    author: str | None = None
    cover_url: str | None = None
    description: str | None = None

    def to_ref(self) -> WorkRef:
        extra = asdict(self)
        extra.pop("id")
        extra["languages"] = [BNR_LANGUAGE]
        return WorkRef(
            id=self.id,
            source=BNR_SOURCE,
            extra=extra,
        )


@dataclass(frozen=True, slots=True)
class Page:
    """A sub-page of the catalogue, as listed by its navigation feed."""

    id: str
    url: str


class BibliothequeNumeriqueRomandeCatalog(CatalogPort):
    """Discover Bibliothèque numérique romande books from OPDS feeds."""

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
                "Bibliothèque numérique romande only offers EPUB; no requested format "
                "can be downloaded"
            )
            return []

        requested_categories = {
            normalize_category(category)
            for category in filters.options.get("categories") or []
        }
        if requested_categories:
            available = {normalize_category(name) for name in COLLECTION_ORDER}
            unknown = sorted(requested_categories - available)
            if unknown:
                critical_error(
                    "No Bibliothèque numérique romande category matches "
                    f"{', '.join(unknown)!r}. Available categories: "
                    f"{', '.join(self.list_categories())}. "
                    "Use --list-bnr-categories to browse them."
                )

        pages = self._select_filter_pages(filters)
        # The same book is listed once per category/series page it belongs to, so
        # keep only its first occurrence.
        books_by_id: dict[str, BNRCatalogBook] = {}
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

        return [book.to_ref() for book in books]

    def _select_filter_pages(self, filters: CatalogFilters) -> list[Page]:
        """
        Select the pages that correspond to the specific filter.

        BNR website filters are mutually exclusive. The available filters are
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
            # Categories are the collapsed collections, not BNR tags, so the
            # whole title index is fetched
            return self._list_titles()
        elif inputs := filters.options.get("title"):
            filter_kind = "title prefixes"
            pages = self._list_titles()
        else:
            # No filter means the whole catalogue
            return self._list_titles()

        requested = {(normalize(value) or "").strip().casefold() for value in inputs}
        matching = [
            page for page in pages if (normalize(page.id) or "").casefold() in requested
        ]
        if not matching:
            available = ", ".join(self._sorted_page_ids(pages)) or "(none)"
            critical_error(
                "No Bibliothèque numérique romande "
                f"{filter_kind} matches {', '.join(inputs)!r}. "
                f"Available {filter_kind}: {available}. "
                "Use --list-bnr-* to browse them."
            )
        return matching

    def list_series(self) -> list[str]:
        """Return every series name available on BNR, sorted alphabetically."""
        return self._sorted_page_ids(self._list_series())

    def list_authors(self) -> list[str]:
        """Return every author name available on BNR, sorted alphabetically."""
        return self._sorted_page_ids(self._list_authors())

    def list_categories(self) -> list[str]:
        """Return the broad collection names used for BNR works, sorted."""
        return sorted(COLLECTION_ORDER, key=str.casefold)

    def list_titles(self) -> list[str]:
        """Return every title prefix available on BNR, sorted alphabetically."""
        return self._sorted_page_ids(self._list_titles())

    @staticmethod
    def _sorted_page_ids(pages: Iterable[Page]) -> list[str]:
        """Return distinct page ids, sorted case-insensitively."""
        return sorted({page.id for page in pages}, key=str.casefold)

    def _list_series(self) -> list[Page]:
        """List the available series pages on BNR"""
        return self._list_navigation_entries("cops:series")

    def _list_authors(self) -> list[Page]:
        """List the available author pages on BNR"""
        # The authors's listing lists the authors index sorted alphabetically.
        # Fetch those individiual pages to get the list of authors on BNR
        entries = self._list_navigation_entries("cops:authors")
        authors: list[Page] = []
        for entry in entries:
            authors.extend(
                self._parse_navigation_feed(
                    self._engine.fetch_bytes(entry.url).decode("utf-8")
                )
            )
        return authors

    def _list_titles(self) -> list[Page]:
        """List the available title pages on BNR"""
        return self._list_navigation_entries("cops:books")

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

            navigation = entry.find(
                "atom:link[@type='application/atom+xml;profile=opds-catalog;kind=navigation']",
                NAMESPACES,
            )
            href = (navigation.get("href") if navigation is not None else None) or ""
            href = href.strip()
            if not href:
                return []

            navigation_url = urljoin(self._base_url, href)
            feed = self._engine.fetch_bytes(navigation_url).decode("utf-8")
            return self._parse_navigation_feed(feed)

        return []

    def _parse_navigation_feed(self, xml: str) -> list[Page]:
        """Parse a navigation feed into the pages it lists."""
        root = ET.fromstring(xml)

        pages: list[Page] = []
        for entry in root.findall("atom:entry", NAMESPACES):
            title = _element_text(entry, "atom:title")
            navigation = entry.find(
                "atom:link[@type='application/atom+xml;profile=opds-catalog;kind=navigation']",
                NAMESPACES,
            )
            href = (navigation.get("href") if navigation is not None else None) or ""
            href = href.strip()
            if not title or not href:
                continue

            pages.append(Page(id=title, url=urljoin(self._base_url, href)))

        return pages

    def _parse_books(self, page: Page) -> list[BNRCatalogBook]:
        """Parse a book listings feed into a list of BNRCatalogBook."""
        data = self._engine.fetch_bytes(page.url).decode("utf-8")
        root = ET.fromstring(data)
        books: list[BNRCatalogBook] = []

        for entry in root.findall("atom:entry", NAMESPACES):
            title = _element_text(entry, "atom:title")
            feed_id = _element_text(entry, "atom:id")
            source_url = _acquisition_url(entry, self._base_url)

            if not title or not feed_id or not source_url:
                logger.warning(
                    f"entry at {page.url} does not have title or book ID or "
                    f" source URL; {title=}, {feed_id=}, {source_url=}"
                )
                continue

            books.append(
                BNRCatalogBook(
                    id=uuid_from_feed_id(feed_id),
                    title=title,
                    source_url=source_url,
                    categories=_entry_categories(entry),
                    author=_element_text(entry, "atom:author/atom:name"),
                    cover_url=_link_url(entry, COVER_RELS, self._base_url),
                    description=_element_text(entry, "atom:content"),
                )
            )

        return books
