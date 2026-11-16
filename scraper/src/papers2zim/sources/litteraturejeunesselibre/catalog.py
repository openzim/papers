"""OPDS-backed Littérature jeunesse libre (LJL) discovery.

LJL publishes an index of its catalogue and filters as an OPDS Atom feed ready for
export. Each filter lists all the books in the catalogue that match that specific
criteria. Every entry is self-contained: it carries the title, description, author,
language, thumbnail, source page and ready-made download links for the supported
formats (EPUB and PDF). So a `WorkRef` here already holds everything the metadata
port needs - no per-book fetch
"""

import re
from collections.abc import Iterable
from xml.etree import ElementTree as ET

from papers2zim.constants import logger
from papers2zim.core.categories import normalize_category
from papers2zim.core.fulltext import html_text
from papers2zim.core.language import normalize_language
from papers2zim.core.opds import (
    OpdsBook,
    OpdsCatalog,
    Page,
    element_text,
    element_texts,
    expand_navigation_pages,
    navigation_entries,
    normalize_author,
    parse_book_entry,
    parse_uuid,
    sorted_page_ids,
)
from papers2zim.core.ports import CatalogFilters, CatalogPort, WorkRef
from papers2zim.core.utils import critical_error, normalize
from papers2zim.sources.litteraturejeunesselibre.categories import (
    category_resolver as _category_resolver,
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

# Calibre OPDS feeds prefix the HTML description with the book's tags.
TAGS_PREFIX_RE = re.compile(r"^\s*TAGS\s*:[^<]*(?=<)", re.IGNORECASE)


def _entry_languages(entry: ET.Element) -> list[str]:
    """Normalized, de-duplicated language codes advertised by an entry."""
    languages: list[str] = []
    for value in element_texts(entry, "dcterms:language"):
        code = normalize_language(value)
        if code and code not in languages:
            languages.append(code)
    return languages


def _description(entry: ET.Element) -> str | None:
    """Plain-text description without Calibre's redundant ``TAGS:`` line."""
    value = element_text(entry, "atom:content")
    if not value:
        return None
    value = TAGS_PREFIX_RE.sub("", value, count=1)
    return html_text(value) or None


class LitteratureJeunesseLibreCatalog(OpdsCatalog, CatalogPort):
    """Discover Littérature jeunesse libre books from OPDS feeds."""

    source = LJL_SOURCE
    source_label = "Littérature jeunesse libre"
    supported_formats = SUPPORTED_FORMATS
    format_by_media_type = FORMAT_BY_MEDIA_TYPE
    category_resolver = _category_resolver
    default_base_url = BASE_URL
    cli_prefix = "ljl"

    def discover(self, filters: CatalogFilters) -> Iterable[WorkRef]:
        requested_formats = set(filters.formats or self.supported_formats)
        if not requested_formats.intersection(self.supported_formats):
            logger.info(
                "%s does not offer any requested format; no books can be downloaded",
                self.source_label,
            )
            return []

        requested_categories = {
            normalize_category(category)
            for category in filters.options.get("categories") or []
        }
        if requested_categories:
            available = {
                normalize_category(name) for name in self.category_resolver.order
            }
            unknown = sorted(requested_categories - available)
            if unknown:
                critical_error(
                    f"No {self.source_label} category matches "
                    f"{', '.join(unknown)!r}. Available categories: "
                    f"{', '.join(self.list_categories())}. "
                    f"Use --list-{self.cli_prefix}-categories to browse them."
                )

        # The same book is listed once per category/series page it belongs to,
        # so keep only its first occurrence.
        books_by_id: dict[str, OpdsBook] = {}
        for page in self._select_filter_pages(filters):
            for book in self.parse_books(page):
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
            critical_error(f"No {self.source_label} books were discovered")

        return [book.to_ref(self.source) for book in books]

    def _select_filter_pages(self, filters: CatalogFilters) -> list[Page]:
        """Select the pages matching the source's mutually exclusive filters."""
        if inputs := filters.options.get("series"):
            filter_kind = "series"
            pages = self._list_series()
        elif inputs := filters.options.get("authors"):
            filter_kind = "authors"
            pages = self._list_authors()
        elif inputs := filters.options.get("categories"):
            # Categories are the collapsed collections, not raw source tags, so
            # the whole title index is fetched.
            return self._list_titles()
        elif inputs := filters.options.get("title"):
            filter_kind = "title prefixes"
            pages = self._list_titles()
        else:
            # No filter means the whole catalogue.
            return self._list_titles()

        if filter_kind == "authors":
            requested = {normalize_author(value) for value in inputs}
            matching = [
                page for page in pages if normalize_author(page.id) in requested
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
            available = ", ".join(sorted_page_ids(pages)) or "(none)"
            critical_error(
                f"No {self.source_label} {filter_kind} matches "
                f"{', '.join(inputs)!r}. Available {filter_kind}: {available}. "
                f"Use --list-{self.cli_prefix}-* to browse them."
            )
        return matching

    def list_series(self) -> list[str]:
        return sorted_page_ids(self._list_series())

    def list_authors(self) -> list[str]:
        return sorted_page_ids(self._list_authors())

    def list_categories(self) -> list[str]:
        return sorted(self.category_resolver.order, key=str.casefold)

    def list_titles(self) -> list[str]:
        return sorted_page_ids(self._list_titles())

    def _navigation_entries(self, entry_id: str) -> list[Page]:
        return navigation_entries(self._engine, self._base_url, entry_id)

    def _list_series(self) -> list[Page]:
        # LJL nests the series under alphabetic index pages.
        return expand_navigation_pages(
            self._engine,
            self._navigation_entries("/bbs/opds/series"),
        )

    def _list_authors(self) -> list[Page]:
        # LJL nests the authors under alphabetic index pages.
        return expand_navigation_pages(
            self._engine,
            self._navigation_entries("/bbs/opds/author"),
        )

    def _list_titles(self) -> list[Page]:
        return self._navigation_entries("/bbs/opds/books")

    def book_from_entry(self, entry: ET.Element, feed_url: str) -> OpdsBook | None:
        return parse_book_entry(
            entry,
            base_url=self._base_url,
            feed_url=feed_url,
            formats_by_media_type=self.format_by_media_type,
            category_resolver=self.category_resolver,
            languages=_entry_languages(entry),
            description=_description(entry),
        )
