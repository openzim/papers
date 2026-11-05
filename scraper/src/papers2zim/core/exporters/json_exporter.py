"""JSON files exporter for the frontend UI (moved from `papers2zim.export`).

Generates books.json, authors.json, collections JSON, config.json, and the
per-item detail JSON files. The ZIM search index entries pointing at the
UI routes live in `search_items_exporter`.
"""

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from papers2zim.constants import logger
from papers2zim.core.index_builder import Indexes
from papers2zim.core.models import Creator, Work
from papers2zim.core.schemas import (
    Author as AuthorSchema,
)
from papers2zim.core.schemas import (
    AuthorDetail,
    AuthorPreview,
    AuthorRef,
    Authors,
    BookFormat,
    BookPreview,
    BooksManifest,
    BooksPage,
    Collection,
    CollectionPreview,
    Collections,
    Config,
    FeatureFlags,
    SourceInfo,
    ThemeConfig,
    ZimContentInfo,
)
from papers2zim.core.schemas import (
    Book as BookSchema,
)
from papers2zim.core.utils import (
    ALL_FORMATS,
    archive_name_for,
    article_name_for,
    collection_key,
    creator_birth_year,
    creator_death_year,
    primary_collection_id,
    primary_creator,
    requested_formats,
)
from papers2zim.core.work_store import WorkStore
from papers2zim.core.zim_assembler import ZimAssembler

# JSON Generation Functions for Vue.js UI

# books.json has no natural per-entity split (unlike collections/authors, one
# file per id), so it's chunked into books-pages/{page}.json files this big.
BOOKS_PAGE_SIZE = 500

# BookPreview.description is a short excerpt for list views; the full text
# only lives on the single-book Book detail schema.
DESCRIPTION_EXCERPT_LENGTH = 200


def _description_excerpt(description: str | None) -> str | None:
    """Short, word-boundary-truncated excerpt of a book's description."""
    if description is None or len(description) <= DESCRIPTION_EXCERPT_LENGTH:
        return description
    truncated = description[:DESCRIPTION_EXCERPT_LENGTH].rsplit(" ", 1)[0]
    return f"{truncated}…"


@dataclass(frozen=True, slots=True)
class LanguageBreakdown:
    """Per-language presence/book-count/popularity for one author or collection"""

    languages: dict[str, list[str]] = field(default_factory=dict)
    book_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    popularities: dict[str, dict[str, float]] = field(default_factory=dict)

    def for_key(self, key: str) -> tuple[list[str], dict[str, int], dict[str, float]]:
        return (
            self.languages.get(key, []),
            self.book_counts.get(key, {}),
            self.popularities.get(key, {}),
        )


def _language_breakdown(works_by_key: dict[str, list[Work]]) -> LanguageBreakdown:
    """Group each key's works by language, once, for O(n) preview exports."""
    languages: dict[str, list[str]] = {}
    book_counts: dict[str, dict[str, int]] = {}
    popularities: dict[str, dict[str, float]] = {}
    for key, works in works_by_key.items():
        counts: dict[str, int] = {}
        popularity: dict[str, float] = {}
        for work in works:
            for lang in work.languages:
                counts[lang] = counts.get(lang, 0) + 1
                popularity[lang] = popularity.get(lang, 0) + (work.popularity or 0)
        languages[key] = sorted(counts)
        book_counts[key] = counts
        popularities[key] = popularity
    return LanguageBreakdown(languages, book_counts, popularities)


def _creator_to_ref(creator: Creator) -> AuthorRef:
    """Convert Creator to the minimal AuthorRef embedded in a BookPreview."""
    return AuthorRef(
        id=creator.id,
        display_name=creator.display_name,
        sort_name=creator.sort_name or "",
    )


def _creator_to_preview(
    creator: Creator,
    author_stats: dict[str, tuple[int, float]],
    author_languages: LanguageBreakdown,
) -> AuthorPreview:
    """Convert Creator to AuthorPreview schema"""
    book_count, total_popularity = author_stats.get(creator.id, (0, 0))
    languages, book_count_by_language, total_popularity_by_language = (
        author_languages.for_key(creator.id)
    )
    return AuthorPreview(
        id=creator.id,
        display_name=creator.display_name,
        sort_name=creator.sort_name or "",
        book_count=book_count,
        total_popularity=total_popularity,
        portrait_path=creator.extra.get("portrait_path"),
        languages=languages,
        book_count_by_language=book_count_by_language,
        total_popularity_by_language=total_popularity_by_language,
    )


def _creator_to_schema(
    creator: Creator,
    author_stats: dict[str, tuple[int, float]],
    author_languages: LanguageBreakdown,
) -> AuthorSchema:
    """Convert Creator to Author schema"""
    book_count, total_popularity = author_stats.get(creator.id, (0, 0))
    languages, book_count_by_language, total_popularity_by_language = (
        author_languages.for_key(creator.id)
    )
    return AuthorSchema(
        id=creator.id,
        sort_name=creator.sort_name or "",
        birth_year=creator_birth_year(creator),
        death_year=creator_death_year(creator),
        display_name=creator.display_name,
        bio=creator.extra.get("bio"),
        portrait_path=creator.extra.get("portrait_path"),
        webpage_resource=creator.extra.get("webpage_resource"),
        book_count=book_count,
        total_popularity=total_popularity,
        languages=languages,
        book_count_by_language=book_count_by_language,
        total_popularity_by_language=total_popularity_by_language,
    )


def _cover_path_for(work: Work) -> str | None:
    has_cover = work.extra.get("has_cover", work.cover is not None)
    return f"covers/{work.id}_cover_image.webp" if has_cover else None


def _work_to_preview(work: Work, formats: list[str]) -> BookPreview:
    """Convert Work to BookPreview schema"""
    return BookPreview(
        id=work.id,
        title=work.title,
        author=_creator_to_ref(primary_creator(work)),
        languages=work.languages,
        popularity=float(work.popularity or 0),
        flames=work.flames or 0,
        cover_path=_cover_path_for(work),
        primary_collection=primary_collection_id(work),
        available_formats=requested_formats(work, formats),
        description=_description_excerpt(work.description),
    )


def _work_to_schema(
    work: Work,
    formats: list[str],
    author_stats: dict[str, tuple[int, float]],
    author_languages: LanguageBreakdown,
) -> BookSchema:
    """Convert Work to Book schema with formats"""
    book_formats: list[BookFormat] = []
    available_formats = requested_formats(work, formats)

    for fmt in formats:
        if fmt in available_formats:
            if fmt == "html":
                path = article_name_for(work)
            else:
                path = archive_name_for(work, fmt)
            book_formats.append(
                BookFormat(
                    format=fmt,
                    path=path,
                    available=True,
                )
            )
        else:
            book_formats.append(
                BookFormat(
                    format=fmt,
                    path="",
                    available=False,
                )
            )

    return BookSchema(
        id=work.id,
        title=work.title,
        subtitle=work.subtitle,
        author=_creator_to_schema(
            primary_creator(work), author_stats, author_languages
        ),
        languages=work.languages,
        license=work.license or "Public domain in the USA.",
        license_id=work.license_id,
        popularity=float(work.popularity or 0),
        flames=work.flames or 0,
        primary_collection=primary_collection_id(work),
        cover_path=_cover_path_for(work),
        formats=book_formats,
        description=work.description,
        published=work.published,
    )


def _collection_to_preview(
    collection_id: str,
    collection_name: str,
    collection_works: list[Work],
    collection_languages: LanguageBreakdown,
) -> CollectionPreview:
    languages, book_count_by_language, total_popularity_by_language = (
        collection_languages.for_key(collection_id)
    )
    return CollectionPreview(
        id=collection_id,
        name=collection_name,
        book_count=len(collection_works),
        total_popularity=sum(work.popularity or 0 for work in collection_works),
        languages=languages,
        book_count_by_language=book_count_by_language,
        total_popularity_by_language=total_popularity_by_language,
    )


def generate_json_files(
    zim_name: str,
    formats: list[str],
    work_store: WorkStore,
    assembler: ZimAssembler,
    title: str | None = None,
    description: str | None = None,
    *,
    display_name: str,
    indexes: Indexes,
    source_slug: str = "source",
    source_description: str | None = None,
    collection_label: str = "Collections",
    collection_icon_style: str = "classification",
    has_popularity: bool = True,
    requested_languages: list[str] | None = None,
    requested_collections: list[str] | None = None,
    books: list[str] | None = None,
    books_page_size: int = BOOKS_PAGE_SIZE,
) -> None:
    """Generate all JSON files for Vue.js frontend"""
    logger.info("Generating JSON files for Vue.js UI")

    # Fetch data once and reuse
    all_works = list(work_store.works)
    all_creators = indexes.authors
    author_stats = indexes.author_stats
    author_languages = _language_breakdown(indexes.by_author)

    logger.info("Generating high-level JSON files")
    logger.debug("Generating books.json and books-pages/*.json")
    books_preview = [_work_to_preview(work, formats) for work in all_works]
    total_pages = (
        math.ceil(len(books_preview) / books_page_size) if books_preview else 0
    )
    manifest = BooksManifest(
        total_count=len(books_preview),
        page_size=books_page_size,
        total_pages=total_pages,
    )
    assembler.add_item_for(
        path="books.json",
        content=manifest.model_dump_json(by_alias=True, indent=2),
        mimetype="application/json",
        is_front=False,
    )
    for page in range(total_pages):
        start = page * books_page_size
        page_content = BooksPage(books=books_preview[start : start + books_page_size])
        assembler.add_item_for(
            path=f"books-pages/{page}.json",
            content=page_content.model_dump_json(by_alias=True, indent=2),
            mimetype="application/json",
            is_front=False,
        )

    logger.debug("Generating authors.json")
    authors_preview = [
        _creator_to_preview(creator, author_stats, author_languages)
        for creator in all_creators
    ]
    authors_collection = Authors(
        authors=authors_preview, total_count=len(authors_preview)
    )

    collection_works_map: dict[str, list[Work]] = defaultdict(list)
    collection_names: dict[str, str] = {}
    for work in all_works:
        for collection in work.collections:
            collection_works_map[collection.id].append(work)
            collection_names.setdefault(collection.id, collection.name)
    collection_ids = sorted(
        collection_works_map,
        key=lambda collection_id: collection_names[collection_id],
    )
    collection_languages = _language_breakdown(collection_works_map)

    collections = Collections(
        collections=[
            _collection_to_preview(
                collection_id,
                collection_names[collection_id],
                collection_works_map[collection_id],
                collection_languages,
            )
            for collection_id in collection_ids
        ],
        total_count=len(collection_ids),
    )
    assembler.add_item_for(
        path="collections.json",
        content=collections.model_dump_json(by_alias=True, indent=2),
        mimetype="application/json",
        is_front=False,
    )
    assembler.add_item_for(
        path="authors.json",
        content=authors_collection.model_dump_json(by_alias=True, indent=2),
        mimetype="application/json",
        is_front=False,
    )

    logger.debug("Generating config.json")
    work_titles_by_id = {work.id: work.title for work in all_works}
    book_languages = sorted({lang for work in all_works for lang in work.languages})
    content_info = ZimContentInfo(
        source=display_name,
        collections=requested_collections or None,
        books=(
            [work_titles_by_id.get(book_id, book_id) for book_id in books]
            if books
            else None
        ),
        languages=requested_languages or None,
        formats=None if set(formats) == set(ALL_FORMATS) else formats,
        date_scraped=date.today().isoformat(),
    )
    config = Config(
        title=title or zim_name or f"{display_name} Library",
        description=description,
        source=SourceInfo(
            slug=source_slug,
            name=display_name,
            description=source_description or display_name,
        ),
        content_info=content_info,
        zim_name=zim_name,
        book_languages=book_languages,
        theme=ThemeConfig(
            format_icons={format_name: format_name for format_name in formats},
            route_labels={
                "home": "Home",
                "works": "eBooks",
                "authors": "Authors",
                "collections": collection_label,
            },
            collection_icon_style=collection_icon_style,
        ),
        features=FeatureFlags(
            epub_reader="epub" in formats,
            pdf_reader="pdf" in formats,
            noscript_fallback=True,
            has_popularity=has_popularity,
            has_multiple_collections=len(collection_ids) > 1,
        ),
    )
    assembler.add_item_for(
        path="config.json",
        content=config.model_dump_json(by_alias=True, indent=2),
        mimetype="application/json",
        is_front=False,
    )

    logger.info("Generating detail JSON files")
    logger.debug("Generating book detail files")
    for work in all_works:
        book_detail = _work_to_schema(work, formats, author_stats, author_languages)
        assembler.add_item_for(
            path=f"books/{work.id}.json",
            content=book_detail.model_dump_json(by_alias=True, indent=2),
            mimetype="application/json",
            is_front=False,
        )

    for collection_id in collection_ids:
        collection_works = collection_works_map[collection_id]
        languages, book_count_by_language, total_popularity_by_language = (
            collection_languages.for_key(collection_id)
        )
        collection = Collection(
            id=collection_id,
            name=collection_names[collection_id],
            book_count=len(collection_works),
            total_popularity=sum(work.popularity or 0 for work in collection_works),
            languages=languages,
            book_count_by_language=book_count_by_language,
            total_popularity_by_language=total_popularity_by_language,
            books=[_work_to_preview(work, formats) for work in collection_works],
        )
        assembler.add_item_for(
            path=f"collections/{collection_key(collection_id)}.json",
            content=collection.model_dump_json(by_alias=True, indent=2),
            mimetype="application/json",
            is_front=False,
        )

    logger.debug("Generating author detail files")
    for creator in all_creators:
        creator_works = [
            _work_to_preview(work, formats)
            for work in indexes.by_author.get(creator.id, [])
        ]
        languages, book_count_by_language, total_popularity_by_language = (
            author_languages.for_key(creator.id)
        )
        author_detail = AuthorDetail(
            id=creator.id,
            sort_name=creator.sort_name or "",
            birth_year=creator_birth_year(creator),
            death_year=creator_death_year(creator),
            display_name=creator.display_name,
            bio=creator.extra.get("bio"),
            portrait_path=creator.extra.get("portrait_path"),
            webpage_resource=creator.extra.get("webpage_resource"),
            books=creator_works,
            book_count=len(creator_works),
            total_popularity=author_stats.get(creator.id, (0, 0))[1],
            languages=languages,
            book_count_by_language=book_count_by_language,
            total_popularity_by_language=total_popularity_by_language,
        )

        assembler.add_item_for(
            path=f"authors/{creator.id}.json",
            content=author_detail.model_dump_json(by_alias=True, indent=2),
            mimetype="application/json",
            is_front=False,
        )

    logger.info("JSON file generation completed")
