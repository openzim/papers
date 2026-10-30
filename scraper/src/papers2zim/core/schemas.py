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
class AuthorPreview(CamelModel):
    """Author preview for list views"""

    id: str
    name: str  # Formatted full name
    sort_name: str  # Opaque sort key (last name, then first name, ...), not for display
    book_count: int
    total_popularity: float = 0
    portrait_path: str | None = None


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

    id: str  # source-specific work id (not necessarily numeric)
    title: str
    author: AuthorPreview
    languages: list[str]
    popularity: float  # Source-specific ranking score
    flames: int = 0
    cover_path: str | None = None
    primary_collection: str | None = None
    available_formats: list[str] = []
    description: str | None = None


class Book(BookPreview):
    """Full book details"""

    subtitle: str | None = None
    license: str
    author: Author
    formats: list[BookFormat]
    description: str | None = None
    published: str | None = None


# Collection Models
class Books(CamelModel):
    """List of book previews"""

    books: list[BookPreview]
    total_count: int


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


# Update forward references for Pydantic v2
BookPreview.model_rebuild()
Book.model_rebuild()
AuthorDetail.model_rebuild()
