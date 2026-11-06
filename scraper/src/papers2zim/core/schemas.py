"""Pydantic schemas for JSON serialization with camelCase conversion"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Model to transform Python snake_case into JSON camelCase."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


# Author Models
class AuthorRef(CamelModel):
    """Minimal author reference, for embedding inside a BookPreview.

    The full AuthorPreview (book_count, per-language breakdowns, etc.) is
    already available via authors/{id}.json and authors.json; repeating it
    on every one of an author's books is what made books.json/collections/
    */authors/* JSON bloat to tens of MB (see issue #138).
    """

    id: str
    display_name: str  # Full name as shown to readers
    sort_name: str  # Last name alone, not for display; tiebreak on display_name


class AuthorPreview(AuthorRef):
    """Author preview for list views"""

    book_count: int
    total_popularity: float = 0
    portrait_path: str | None = None
    # Lets the UI filter/display per-language counts without fetching every
    # author's detail JSON.
    languages: list[str] = []
    book_count_by_language: dict[str, int] = {}
    total_popularity_by_language: dict[str, float] = {}


class Author(AuthorPreview):
    """Author information for JSON export"""

    birth_year: str | None = None
    death_year: str | None = None
    bio: str | None = None
    webpage_resource: str | None = None


class AuthorDetail(Author):
    """Full author details with books list"""

    books: list[BookPreview]


# Book Models
class BookFormat(CamelModel):
    """Available format information"""

    format: str  # "html", "epub", "pdf"
    path: str  # ZIM path to file
    available: bool = True


class BookPreview(CamelModel):
    """Book preview for list views"""

    id: str  # slug of the title, unique in the catalog
    title: str
    author: AuthorRef
    languages: list[str]
    popularity: float  # Source-specific ranking score
    flames: int = 0
    cover_path: str | None = None
    primary_collection: str | None = None
    available_formats: list[str] = []
    # Short excerpt only; the full text lives on the Book detail schema.
    description: str | None = None


class Book(BookPreview):
    """Full book details"""

    subtitle: str | None = None
    license: str
    # Creative Commons identifier (e.g. "CC-BY-SA-3.0") when `license` names one;
    # the UI then shows a localized label and a link instead of `license`
    license_id: str | None = None
    author: Author
    formats: list[BookFormat]
    description: str | None = None
    published: str | None = None


# Collection Models
class BooksManifest(CamelModel):
    """Pagination manifest for the full books catalog (books.json).

    The catalog itself (unlike collections/authors, which are naturally
    split one-file-per-id) has no per-entity split, so it's chunked into
    `books-pages/{order}/{page}.json` files of `page_size` BookPreview each;
    this manifest tells the UI how many pages to fetch, per `order`.

    One set of pages exists per sort criterion the UI offers (`popularity`,
    `title`, `author`), each cut in the direction the UI sorts it by default.
    A prefix of the set a reader is on is therefore what a fully-loaded
    catalog would have shown them first, for any sort, without the UI loading
    the catalog at all. `book_count_by_language` lets it state a language's
    book count without merging every page, counting a multilingual book under
    each of its languages.
    """

    total_count: int
    page_size: int
    total_pages: int
    book_count_by_language: dict[str, int] = {}


class BooksPage(CamelModel):
    """One page of the books catalog."""

    books: list[BookPreview]


class Authors(CamelModel):
    """List of author previews"""

    authors: list[AuthorPreview]
    total_count: int


class CollectionPreview(CamelModel):
    """Collection preview for source-neutral collection views."""

    id: str
    name: str
    book_count: int
    total_popularity: float = 0
    # Same per-language breakdown as `AuthorPreview`, and for the same reason.
    languages: list[str] = []
    book_count_by_language: dict[str, int] = {}
    total_popularity_by_language: dict[str, float] = {}


class Collection(CollectionPreview):
    """Collection detail with its works."""

    books: list[BookPreview]


class Collections(CamelModel):
    """List of collection previews."""

    collections: list[CollectionPreview]
    total_count: int


class SourceInfo(CamelModel):
    """Identity and description of the content source."""

    slug: str
    name: str
    description: str


class ZimContentInfo(CamelModel):
    """Explicit filters used to build this ZIM, for the "About this ZIM" panel.

    A `None` field means that dimension was not filtered at all (displayed
    as "All" in the UI); a list reports the raw filter values as supplied.
    """

    source: str
    collections: list[str] | None = None
    books: list[str] | None = None
    languages: list[str] | None = None
    formats: list[str] | None = None
    date_scraped: str


class ThemeConfig(CamelModel):
    """Source-specific UI presentation settings."""

    format_icons: dict[str, str]
    route_labels: dict[str, str]
    collection_icon_style: str = "classification"


class FeatureFlags(CamelModel):
    """Capabilities available to the UI."""

    epub_reader: bool
    pdf_reader: bool
    noscript_fallback: bool
    has_popularity: bool = True
    has_multiple_collections: bool = True


class Config(CamelModel):
    """UI configuration"""

    title: str
    description: str | None = None
    source: SourceInfo
    theme: ThemeConfig
    features: FeatureFlags
    content_info: ZimContentInfo
    # Stable internal ZIM name/slug, independent of `title` (which may change
    # across rebuilds of the same ZIM); used by the UI to key per-ZIM state
    # such as the persisted interface language choice.
    zim_name: str
    # Distinct language codes actually present across the exported books,
    # regardless of what `--languages` filter (if any) was requested; the
    # source of truth for whether this ZIM is single- or multi-language.
    book_languages: list[str]


# Update forward references for Pydantic v2
BookPreview.model_rebuild()
Book.model_rebuild()
AuthorDetail.model_rebuild()
