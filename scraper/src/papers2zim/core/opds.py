"""Shared helpers for OPDS (Atom) catalogue feeds.

OPDS is the protocol used by several sources to publish their catalogue and
filters. Sources declare their feed layout and how a book entry maps to a
`Work`; pagination, navigation indexes, and entry parsing are shared here.
"""

# ruff: noqa: S314

import re
import unicodedata
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, ClassVar, Protocol
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

from papers2zim.constants import logger
from papers2zim.core.categories import CategoryResolver
from papers2zim.core.models import Format
from papers2zim.core.ports import WorkRef

NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "opds": "http://opds-spec.org/2010/catalog",
    "dcterms": "http://purl.org/dc/terms/",
}

ACQUISITION_REL = "http://opds-spec.org/acquisition"
COVER_RELS = (
    "http://opds-spec.org/image/thumbnail",
    "http://opds-spec.org/image",
)

OPDS_NAVIGATION_TYPE = "application/atom+xml;profile=opds-catalog"

# OPDS feeds paginate through rel="next", and a malformed feed
# could otherwise loop forever. This is far above any realistic catalogue page
# count for a single filter.
MAX_FEED_PAGES = 1000

UUID_RE = re.compile(
    r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}",
    re.IGNORECASE,
)


class FeedEngine(Protocol):
    """Minimal download interface required to read a feed."""

    def fetch_bytes(self, url: str) -> bytes: ...


def normalize_whitespace(value: str | None) -> str | None:
    """Collapse whitespace in value, returning None when it is blank."""
    if value is None:
        return None
    return " ".join(value.split()) or None


def normalize_author(value: str | None) -> str:
    """Order- and accent-independent key for an author name."""
    decomposed = unicodedata.normalize("NFKD", value or "")
    text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(sorted(re.findall(r"\w+", text.casefold())))


def parse_uuid(value: str) -> str | None:
    """Return the canonical UUID of a bare UUID string, or None."""
    text = value.strip()
    return text.casefold() if UUID_RE.fullmatch(text) else None


def parse_entry_id(value: str) -> str:
    """Return the canonical UUID carried in an Atom ``<id>`` value."""
    return re.sub(
        r"^(urn:uuid:)+",
        "",
        value.strip().casefold(),
        flags=re.IGNORECASE,
    )


def element_texts(entry: ET.Element, path: str) -> list[str]:
    """Whitespace-collapsed text of every child matching path, skipping empty values."""
    texts = (
        normalize_whitespace("".join(element.itertext()))
        for element in entry.findall(path, NAMESPACES)
    )
    return [text for text in texts if text]


def element_text(entry: ET.Element, path: str) -> str | None:
    """Whitespace-collapsed text of the first child matching path."""
    texts = element_texts(entry, path)
    return texts[0] if texts else None


def next_page_url(root: ET.Element, feed_url: str) -> str | None:
    """Resolve the rel="next" pagination link of a feed, if any."""
    for link in root.findall("atom:link", NAMESPACES):
        if link.get("rel") != "next":
            continue
        href = (link.get("href") or "").strip()
        if href:
            return urljoin(feed_url, href)
    return None


def link_url(entry: ET.Element, rels: Sequence[str], base_url: str) -> str | None:
    """Resolve the first usable link, trying rels in order."""
    for rel in rels:
        for link in entry.findall("atom:link", NAMESPACES):
            href = (link.get("href") or "").strip()
            if link.get("rel") == rel and href:
                return urljoin(base_url, href)
    return None


def acquisition_urls(
    entry: ET.Element, base_url: str, formats_by_media_type: Mapping[str, str]
) -> list[Format]:
    """Acquisition links of an entry, in formats the source can download."""
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


def entry_category_terms(entry: ET.Element) -> list[str]:
    """Distinct category terms advertised by an entry, in feed order."""
    terms: list[str] = []
    for category in entry.findall("atom:category", NAMESPACES):
        term = normalize_whitespace(category.get("term"))
        if term and term not in terms:
            terms.append(term)
    return terms


def navigation_href(entry: ET.Element, link_type: str) -> str | None:
    """Href of an entry's navigation link of the requested OPDS type."""
    for link in entry.findall("atom:link", NAMESPACES):
        if link.get("type") != link_type:
            continue
        href = (link.get("href") or "").strip()
        if href:
            return href
    return None


def iter_feed(
    engine: FeedEngine,
    feed_url: str,
    xml: str | None = None,
    *,
    max_pages: int = MAX_FEED_PAGES,
) -> Iterator[tuple[ET.Element, str]]:
    """Yield each page of an OPDS feed, following ``rel="next"`` links."""
    seen = {feed_url}
    current_url = feed_url
    data = xml if xml is not None else engine.fetch_bytes(feed_url).decode("utf-8")

    while True:
        root = ET.fromstring(data)
        yield root, current_url

        next_url = next_page_url(root, current_url)
        if next_url is None:
            return
        if next_url in seen:
            logger.warning(f"Pagination loop detected at {next_url}; stopping")
            return
        if len(seen) >= max_pages:
            logger.warning(f"Stopped paginating {feed_url} after {max_pages} pages")
            return

        seen.add(next_url)
        current_url = next_url
        data = engine.fetch_bytes(next_url).decode("utf-8")


@dataclass(frozen=True, slots=True)
class Page:
    """A sub-page of the catalogue, as listed by its navigation feed."""

    id: str
    url: str


def sorted_page_ids(pages: Iterable[Page]) -> list[str]:
    """Return distinct page ids, sorted case-insensitively."""
    return sorted({page.id for page in pages}, key=str.casefold)


def parse_navigation_feed(
    engine: FeedEngine,
    xml: str,
    feed_url: str,
    *,
    link_type: str,
    skip_titles: Iterable[str] = (),
    max_pages: int = MAX_FEED_PAGES,
) -> list[Page]:
    """Parse a navigation feed and every page linked by ``rel="next"``."""
    skipped = set(skip_titles)
    pages: list[Page] = []

    for root, page_url in iter_feed(engine, feed_url, xml, max_pages=max_pages):
        for entry in root.findall("atom:entry", NAMESPACES):
            title = element_text(entry, "atom:title")
            if not title or title in skipped:
                continue
            href = navigation_href(entry, link_type)
            if not href:
                continue
            pages.append(Page(id=title, url=urljoin(page_url, href)))

    return pages


def home_navigation_url(
    engine: FeedEngine, base_url: str, entry_id: str, *, link_type: str
) -> str | None:
    """URL of the index linked from the home entry whose id is ``entry_id``."""
    data = engine.fetch_bytes(base_url).decode("utf-8")
    root = ET.fromstring(data)

    for entry in root.findall("atom:entry", NAMESPACES):
        if element_text(entry, "atom:id") != entry_id:
            continue
        href = navigation_href(entry, link_type)
        return urljoin(base_url, href) if href else None

    return None


def navigation_entries(
    engine: FeedEngine,
    base_url: str,
    entry_id: str,
    *,
    link_type: str = OPDS_NAVIGATION_TYPE,
    skip_titles: Iterable[str] = ("All",),
) -> list[Page]:
    """Pages listed by the index linked from the home entry ``entry_id``."""
    navigation_url = home_navigation_url(
        engine, base_url, entry_id, link_type=link_type
    )
    if navigation_url is None:
        return []
    return parse_navigation_feed(
        engine,
        engine.fetch_bytes(navigation_url).decode("utf-8"),
        navigation_url,
        link_type=link_type,
        skip_titles=skip_titles,
    )


def expand_navigation_pages(
    engine: FeedEngine,
    entries: Iterable[Page],
    *,
    link_type: str = OPDS_NAVIGATION_TYPE,
    skip_titles: Iterable[str] = ("All",),
) -> list[Page]:
    """Replace navigation index pages by the pages each of them lists."""
    pages: list[Page] = []
    for entry in entries:
        pages.extend(
            parse_navigation_feed(
                engine,
                engine.fetch_bytes(entry.url).decode("utf-8"),
                entry.url,
                link_type=link_type,
                skip_titles=skip_titles,
            )
        )
    return pages


@dataclass(frozen=True, slots=True)
class OpdsBook:
    """A book card parsed from an OPDS entry."""

    id: str
    title: str
    formats: list[Format]
    categories: list[str]
    languages: list[str]
    authors: list[str]
    cover_url: str | None = None
    description: str | None = None

    def to_ref(self, source: str) -> WorkRef:
        extra = asdict(self)
        extra.pop("id")
        extra["formats"] = list(self.formats)
        return WorkRef(id=self.id, source=source, extra=extra)


def formats_from_extra(extra: Mapping[str, Any]) -> list[Format]:
    """Work formats from a `WorkRef.extra`, accepting `Format` objects or dicts."""
    formats: list[Format] = []
    for value in extra.get("formats") or []:
        if isinstance(value, Format):
            formats.append(value)
        elif isinstance(value, Mapping):
            formats.append(Format(**dict(value)))
    return formats


def parse_book_entry(
    entry: ET.Element,
    *,
    base_url: str,
    feed_url: str,
    formats_by_media_type: Mapping[str, str],
    category_resolver: CategoryResolver,
    languages: Sequence[str],
    description: str | None,
) -> OpdsBook | None:
    """Map one OPDS book entry, or return None when it is not usable.

    Sources only supply their language and description policy; the title,
    stable ID, formats, categories, authors, and cover are parsed uniformly.
    """
    title = element_text(entry, "atom:title")
    feed_id = element_text(entry, "atom:id")
    formats = acquisition_urls(entry, base_url, formats_by_media_type)

    if not title or not feed_id or not formats:
        logger.warning(
            f"entry at {feed_url} does not have title or book ID or "
            f"supported download link; {title=}, {feed_id=}, {formats=}"
        )
        return None

    return OpdsBook(
        id=parse_entry_id(feed_id),
        title=title,
        formats=formats,
        categories=category_resolver.collections_for(entry_category_terms(entry)),
        languages=list(languages),
        authors=element_texts(entry, "atom:author/atom:name"),
        cover_url=link_url(entry, COVER_RELS, base_url),
        description=description,
    )


class OpdsCatalog(ABC):
    """Shared OPDS entry parsing.

    Sources own discovery, navigation layout, and list operations; this base
    only provides feed pagination and entry-to-book delegation.
    """

    default_base_url: ClassVar[str]

    def __init__(self, engine: FeedEngine, base_url: str | None = None, **_: object):
        self._engine = engine
        self._base_url = (base_url or self.default_base_url).rstrip("/")

    def parse_books(self, page: Page) -> list[OpdsBook]:
        books: list[OpdsBook] = []
        for root, feed_url in iter_feed(self._engine, page.url):
            for entry in root.findall("atom:entry", NAMESPACES):
                book = self.book_from_entry(entry, feed_url)
                if book is not None:
                    books.append(book)
        return books

    @abstractmethod
    def book_from_entry(self, entry: ET.Element, feed_url: str) -> OpdsBook | None:
        """Map one book entry, or return None when it is not usable."""
