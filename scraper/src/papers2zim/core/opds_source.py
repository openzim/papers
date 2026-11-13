"""Reusable source adapters for self-contained OPDS catalogues.

When an OPDS entry already carries everything about a book (formats, cover URL,
description, authors, ...), a source does not need per-book pages. `OpdsMetadata`,
`OpdsFormatResolver`, and `OpdsPipeline` implement that flow once; a source only
supplies its slug, display label, and default languages.
"""

from collections.abc import Iterable, Iterator
from typing import Any, ClassVar

import requests

from papers2zim.constants import logger
from papers2zim.core.content_validation import is_html_document, is_valid_book_file
from papers2zim.core.covers import extract_cover, fetch_page_cover
from papers2zim.core.download_engine import DownloadEngine, is_fatal_http_error
from papers2zim.core.epub_optimizer import optimize_epub_bytes
from papers2zim.core.language import normalize_language
from papers2zim.core.models import CollectionRef, Cover, Creator, Work
from papers2zim.core.opds import formats_from_extra
from papers2zim.core.pipeline import Pipeline
from papers2zim.core.ports import (
    DownloadRequest,
    FormatResolverPort,
    MetadataPort,
    WorkRef,
)
from papers2zim.core.utils import archive_name_for, author_id, slug_id


class OpdsMetadata(MetadataPort):
    """Map self-contained OPDS book references into works."""

    source: ClassVar[str]
    default_languages: ClassVar[tuple[str, ...]] = ()

    def fetch(self, refs: Iterable[WorkRef]) -> Iterator[Work]:
        for ref in refs:
            yield self.to_work(ref)

    @classmethod
    def to_work(cls, ref: WorkRef) -> Work:
        extra = ref.extra
        formats = formats_from_extra(extra)
        languages: list[str] = []
        for value in _texts(extra.get("languages")):
            if (code := cls.language_code(value)) and code not in languages:
                languages.append(code)
        cover_url = extra.get("cover_url")
        return Work(
            id=ref.id,
            source=cls.source,
            title=extra.get("title") or "Untitled",
            creators=[
                Creator(id=author_id(name), display_name=name, sort_name=name)
                for name in _texts(extra.get("authors"))
            ],
            languages=languages or list(cls.default_languages),
            formats=formats,
            cover=Cover(source_url=cover_url) if cover_url else None,
            collections=[
                CollectionRef(id=slug_id(name), name=name, kind="category")
                for name in _texts(extra.get("categories"))
            ],
            description=extra.get("description"),
            source_url=next((fmt.url for fmt in formats if fmt.url), None),
        )

    @staticmethod
    def language_code(value: str) -> str | None:
        """Normalize one source language code to ISO 639-1 when possible."""
        return normalize_language(value)


class OpdsFormatResolver(FormatResolverPort):
    """Resolve a format from the download links already stored on the work."""

    def resolve(self, work: Work, format_name: str) -> DownloadRequest | None:
        url = next(
            (fmt.url for fmt in work.formats if fmt.name == format_name and fmt.url),
            None,
        )
        if url is None:
            return None
        return DownloadRequest(url=url, format_name=format_name)


class OpdsPipeline(Pipeline):
    """Download self-contained OPDS editions and expose them to the UI readers."""

    def __init__(self, *, engine: DownloadEngine, **kwargs):
        super().__init__(**kwargs)
        self.engine = engine
        self.resolver = OpdsFormatResolver()

    def process_ref(self, ref: WorkRef) -> None:
        works = list(self.metadata.fetch([ref]))
        if not works:
            return
        work = works[0]
        unsupported = work.extra.setdefault("unsupported_formats", [])

        contents: dict[str, bytes] = {}
        cover_image: bytes | None = None
        for format_name in self.formats:
            content = self._download_format(work, format_name, unsupported)
            if content is None:
                continue
            contents[format_name] = content
            if cover_image is None:
                cover_image = extract_cover(
                    content,
                    format_name,
                    declared_only=format_name == "epub",
                )

        if not contents:
            logger.warning(
                "%s book %s has no downloadable requested format",
                self.display_name,
                work.id,
            )
            return

        if cover_image is None:
            cover_image = fetch_page_cover(
                self.engine, work.cover.source_url if work.cover else None
            )
        if cover_image is not None:
            self.assembler.add_item_for(
                path=f"covers/{work.id}_cover_image.webp",
                content=cover_image,
                mimetype="image/webp",
                is_front=False,
            )
            work.cover = Cover()
            work.extra["has_cover"] = True
        else:
            work.extra["has_cover"] = False

        self.store.add(work)
        self.add_book_search_item(work, contents)

    def _download_format(
        self, work: Work, format_name: str, unsupported: list[str]
    ) -> bytes | None:
        request = self.resolver.resolve(work, format_name)
        if request is None:
            unsupported.append(format_name)
            return None
        try:
            content = self.engine.fetch_bytes(request.url)
        except requests.RequestException as exc:
            log = logger.debug if is_fatal_http_error(exc) else logger.warning
            log(
                "Could not download %s for %s book %s: %s",
                format_name,
                self.display_name,
                work.id,
                exc,
            )
            unsupported.append(format_name)
            return None

        if is_html_document(content) or not is_valid_book_file(content, format_name):
            logger.warning(
                "%s book %s returned an invalid %s response: %s",
                self.display_name,
                work.id,
                format_name.upper(),
                request.url,
            )
            unsupported.append(format_name)
            return None

        if format_name == "epub":
            content = optimize_epub_bytes(
                content,
                log_context=f"{self.display_name} book {work.id}",
            )

        media_type = next(
            (
                book_format.media_type
                for book_format in work.formats
                if book_format.name == format_name
            ),
            None,
        )
        if media_type is None:
            unsupported.append(format_name)
            return None

        self.assembler.add_item_for(
            path=archive_name_for(work, format_name),
            content=content,
            mimetype=media_type,
            is_front=False,
        )
        return content


def _texts(values: Any) -> list[str]:
    """Non-empty strings from a feed-provided list."""
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str) and value.strip()]
