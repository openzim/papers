"""Per-work processing for One More Library."""

from pathlib import Path

import requests

from papers2zim.constants import logger
from papers2zim.core.content_validation import is_valid_book_file
from papers2zim.core.covers import extract_cover
from papers2zim.core.download_engine import DownloadEngine, is_fatal_http_error
from papers2zim.core.epub_optimizer import optimize_epub_bytes
from papers2zim.core.models import Cover
from papers2zim.core.pipeline import Pipeline
from papers2zim.core.ports import WorkRef
from papers2zim.core.utils import archive_name_for
from papers2zim.sources.onemorelibrary.catalog import SUPPORTED_FORMATS
from papers2zim.sources.onemorelibrary.covers import fetch_page_cover
from papers2zim.sources.onemorelibrary.metadata import FORMAT_MEDIA_TYPES
from papers2zim.sources.onemorelibrary.resolver import (
    OnemorelibraryFormatResolver,
)


class OnemorelibraryPipeline(Pipeline):
    """Download EPUB/PDF editions and expose them to the UI readers."""

    def __init__(
        self, *, engine: DownloadEngine, cache_dir: Path | None = None, **kwargs
    ):
        del cache_dir  # accepted for a uniform pipeline constructor
        super().__init__(**kwargs)
        self.engine = engine
        self.resolver = OnemorelibraryFormatResolver()

    def process_ref(self, ref: WorkRef) -> None:
        works = list(self.metadata.fetch([ref]))
        if not works:
            return
        work = works[0]
        unsupported = work.extra.setdefault("unsupported_formats", [])
        downloaded: list[str] = []
        cover_image: bytes | None = None

        for format_name in self.formats:
            if format_name not in SUPPORTED_FORMATS:
                unsupported.append(format_name)
                continue
            request = self.resolver.resolve(work, format_name)
            if request is None:
                unsupported.append(format_name)
                continue
            try:
                content = self.engine.fetch_bytes(request.url)
            except requests.RequestException as exc:
                log = logger.debug if is_fatal_http_error(exc) else logger.warning
                log(
                    "Could not download %s for One More Library book #%s: %s",
                    format_name,
                    work.id,
                    exc,
                )
                unsupported.append(format_name)
                continue
            if not is_valid_book_file(content, format_name):
                logger.warning(
                    "One More Library book #%s returned an invalid %s file",
                    work.id,
                    format_name.upper(),
                )
                unsupported.append(format_name)
                continue

            if format_name == "epub":
                content = optimize_epub_bytes(
                    content, log_context=f"One More Library book {work.id}"
                )

            media_type = next(
                (
                    book_format.media_type
                    for book_format in work.formats
                    if book_format.name == format_name
                ),
                FORMAT_MEDIA_TYPES[format_name],
            )
            self.assembler.add_item_for(
                path=archive_name_for(work, format_name),
                content=content,
                mimetype=media_type,
                is_front=False,
            )
            downloaded.append(format_name)
            if cover_image is None:
                cover_image = extract_cover(
                    content,
                    format_name,
                    declared_only=format_name == "epub",
                )

        if not downloaded:
            logger.warning(
                "One More Library book #%s has no downloadable requested format",
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
