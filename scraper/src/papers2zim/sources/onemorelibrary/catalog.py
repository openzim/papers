"""One More Library catalog discovery.

The site publishes one global paginated listing at
``/index.php/en/books?start=N`` (32 book cards per page). Crawling that
listing once gives every book with its title, author, language and primary
category; individual book pages are only fetched later by the metadata
adapter. The parsed listing is cached in the optional cache directory so
repeated scrapes do not re-crawl the whole collection.
"""

import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from papers2zim.constants import logger
from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.ports import CatalogFilters, CatalogPort, WorkRef
from papers2zim.core.utils import atomic_write_text, critical_error
from papers2zim.sources.onemorelibrary.languages import (
    language_code,
    normalize_language_name,
)

OML_SOURCE = "onemorelibrary"
CATALOG_FILENAME = "onemorelibrary_catalog.json"
LISTING_PATH = "/index.php/en/books"
SUPPORTED_FORMATS = frozenset({"epub", "pdf"})
MAX_PAGES = 2000

_BOOK_ID_RE = re.compile(r"-(\d+)$")


@dataclass(frozen=True, slots=True)
class OmlCatalogBook:
    """A book card from the One More Library listing."""

    id: str
    title: str
    source_url: str
    language: str | None = None
    language_name: str | None = None
    category_id: str | None = None
    category_name: str | None = None
    author: str | None = None
    cover_url: str | None = None
    description: str | None = None

    def to_ref(self) -> WorkRef:
        extra = asdict(self)
        extra.pop("id")
        return WorkRef(
            id=self.id,
            source=OML_SOURCE,
            extra={
                **extra,
                "languages": [self.language] if self.language else [],
            },
        )


def _text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split())


def parse_listing(html: str | bytes, base_url: str) -> list[OmlCatalogBook]:
    """Parse the book cards of one listing page."""
    soup = BeautifulSoup(html, "html.parser")
    books: list[OmlCatalogBook] = []
    for card in soup.select(".item_box"):
        title_link = card.select_one(".title h2 a[href]") or card.select_one(
            ".item_img a[href]"
        )
        if title_link is None:
            continue
        href = title_link.get("href")
        if not isinstance(href, str):
            continue
        match = _BOOK_ID_RE.search(urlparse(href).path.rstrip("/").rsplit("/", 1)[-1])
        if match is None:
            continue

        category_link = card.select_one(".category a[href]")
        category_href = category_link.get("href") if category_link is not None else None
        category_id = (
            urlparse(category_href).path.rstrip("/").rsplit("/", 1)[-1]
            if isinstance(category_href, str)
            else None
        )
        language_node = card.select_one(".type_button")
        language_name = _text(language_node) if language_node is not None else None
        region_node = card.select_one(".author_blog .author_blog_link")
        author = None
        if region_node is not None:
            author = _text(region_node).split(" · ", 1)[0].strip() or None
        if not language_name:
            language_name = (
                _text(region_node).split(" · ", 1)[1].strip()
                if region_node is not None and " · " in _text(region_node)
                else None
            )
        cover = card.select_one(".item_img img[src]")
        cover_src = cover.get("src") if cover is not None else None
        description = card.select_one(".item_desc .desc_info")

        books.append(
            OmlCatalogBook(
                id=match.group(1),
                title=_text(title_link),
                source_url=urljoin(base_url, href),
                language=language_code(language_name),
                language_name=language_name,
                category_id=category_id,
                category_name=(
                    _text(category_link) if category_link is not None else None
                ),
                author=author,
                cover_url=(
                    urljoin(base_url, cover_src) if isinstance(cover_src, str) else None
                ),
                description=(_text(description) if description is not None else None),
            )
        )
    return books


def _pagination_starts(html: str | bytes) -> list[int]:
    """Return every ``start`` query value advertised by the pagination links."""
    soup = BeautifulSoup(html, "html.parser")
    starts: set[int] = set()
    for link in soup.select("a[href]"):
        href = link.get("href")
        if not isinstance(href, str):
            continue
        values = parse_qs(urlparse(href).query).get("start")
        if values and values[0].isdigit():
            starts.add(int(values[0]))
    return sorted(starts)


class OnemorelibraryCatalog(CatalogPort):
    """Discover books from the One More Library paginated listing."""

    BASE_URL = "https://onemorelibrary.com"

    def __init__(
        self,
        engine: DownloadEngine,
        base_url: str = BASE_URL,
        cache_dir: Path | None = None,
        *,
        refresh_catalog: bool = False,
        **_: object,
    ):
        self._engine = engine
        self._base_url = base_url.rstrip("/")
        self._cache_path = cache_dir.resolve() / CATALOG_FILENAME if cache_dir else None
        self._refresh_catalog = refresh_catalog

    @property
    def listing_url(self) -> str:
        return f"{self._base_url}{LISTING_PATH}"

    def discover(self, filters: CatalogFilters) -> Iterable[WorkRef]:
        requested_formats = set(filters.formats or SUPPORTED_FORMATS)
        if not requested_formats.intersection(SUPPORTED_FORMATS):
            logger.info(
                "One More Library only offers EPUB and PDF; no requested format "
                "can be downloaded"
            )
            return []

        books = self._load_catalog()
        total = len(books)

        source_book_ids = {
            str(book_id) for book_id in filters.options.get("book_ids", [])
        }
        positions = {
            int(book_id)
            for book_id in filters.book_ids or []
            if book_id.strip().isdigit()
        }
        if source_book_ids:
            if filters.languages or filters.collections:
                logger.info(
                    "Ignoring language/category filters for explicitly requested "
                    "One More Library book IDs"
                )
            selected = [book for book in books if book.id in source_book_ids]
        elif positions:
            if filters.languages or filters.collections:
                logger.info(
                    "Ignoring language/category filters for explicitly requested "
                    "One More Library book positions"
                )
            selected = [
                book
                for position, book in enumerate(books, start=1)
                if position in positions
            ]
        else:
            selected = self._filter_books(books, filters)

        logger.info(
            "  Selected %s One More Library books from %s catalog entries"
            " (languages: %s, categories: %s)",
            len(selected),
            total,
            filters.languages or "all",
            filters.collections or "all",
        )
        return [book.to_ref() for book in selected]

    @staticmethod
    def _filter_books(
        books: list[OmlCatalogBook], filters: CatalogFilters
    ) -> list[OmlCatalogBook]:
        if filters.languages:
            wanted = {language.casefold() for language in filters.languages}
            books = [book for book in books if (book.language or "") in wanted]

        requested_categories = {
            normalize_language_name(category)
            for category in filters.collections or []
            if category.strip()
        }
        if requested_categories:
            books = [
                book
                for book in books
                if (
                    book.category_name
                    and normalize_language_name(book.category_name)
                    in requested_categories
                )
                or (
                    book.category_id
                    and normalize_language_name(book.category_id)
                    in requested_categories
                )
            ]
        return books

    def list_categories(self) -> list[tuple[str, str]]:
        """Return ``(name, id)`` pairs for every category, sorted by name."""
        categories: dict[str, str] = {}
        for book in self._load_catalog():
            if book.category_id and book.category_name:
                categories.setdefault(book.category_id, book.category_name)
        return sorted(
            ((name, category_id) for category_id, name in categories.items()),
            key=lambda item: item[0].casefold(),
        )

    def refresh(self) -> None:
        """Re-crawl and cache the catalog without selecting any book."""
        if self._cache_path is None:
            critical_error("--refresh-oml-catalog requires --cache-dir")
        self._save(self._crawl())

    def _fetch_listing(self, start: int) -> str:
        url = f"{self.listing_url}?start={start}"
        logger.debug("Fetching One More Library catalog page %s", url)
        return self._engine.fetch_bytes(url).decode("utf-8", errors="replace")

    def _crawl(self) -> list[OmlCatalogBook]:
        logger.info("Crawling One More Library catalog from %s", self.listing_url)
        books: list[OmlCatalogBook] = []
        visited: set[int] = set()
        pending: list[int] = [0]

        while pending and len(visited) < MAX_PAGES:
            start = pending.pop(0)
            if start in visited:
                continue
            visited.add(start)
            page = self._fetch_listing(start)
            books.extend(parse_listing(page, self._base_url))
            pending.extend(
                discovered
                for discovered in _pagination_starts(page)
                if discovered not in visited and discovered not in pending
            )
            pending.sort()

        if pending:
            logger.warning(
                "One More Library advertises more than %s catalog pages; "
                "only the first %s will be crawled",
                MAX_PAGES,
                MAX_PAGES,
            )

        deduplicated: dict[str, OmlCatalogBook] = {}
        for book in books:
            deduplicated.setdefault(book.id, book)
        logger.info(
            "Discovered %s One More Library books across %s listing pages",
            len(deduplicated),
            len(visited),
        )
        return list(deduplicated.values())

    def _save(self, books: list[OmlCatalogBook]) -> None:
        if self._cache_path is None:
            return
        payload = {"version": 1, "books": [asdict(book) for book in books]}
        atomic_write_text(self._cache_path, json.dumps(payload, ensure_ascii=False))

    def _read_cache(self) -> list[OmlCatalogBook] | None:
        if self._cache_path is None or not self._cache_path.exists():
            return None
        try:
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
            return [OmlCatalogBook(**book) for book in payload["books"]]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.warning(
                "Ignoring unreadable One More Library catalog cache %s: %s",
                self._cache_path,
                exc,
            )
            return None

    def _load_catalog(self) -> list[OmlCatalogBook]:
        if self._refresh_catalog:
            books = self._crawl()
            self._save(books)
            return books
        cached = self._read_cache()
        if cached is not None:
            logger.info("Using cached One More Library catalog at %s", self._cache_path)
            return cached
        if self._cache_path is not None:
            logger.info(
                "Downloading One More Library catalog (cache: %s)", self._cache_path
            )
        books = self._crawl()
        self._save(books)
        return books
