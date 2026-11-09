"""Per-work processing for USAID DEC Archive reports."""

import requests

from papers2zim.constants import logger
from papers2zim.core.content_validation import is_valid_book_file
from papers2zim.core.covers import extract_cover
from papers2zim.core.download_engine import DownloadEngine, is_fatal_http_error
from papers2zim.core.models import Cover
from papers2zim.core.pipeline import Pipeline
from papers2zim.core.ports import WorkRef
from papers2zim.core.utils import archive_name_for
from papers2zim.sources.usaiddec.catalog import SUPPORTED_FORMATS
from papers2zim.sources.usaiddec.resolver import UsaidDecFormatResolver


class UsaidDecPipeline(Pipeline):
    """Download USAID DEC evaluation report PDFs and add them to the ZIM."""

    def __init__(self, *, engine: DownloadEngine, **kwargs):
        super().__init__(**kwargs)
        self.engine = engine
        self.resolver = UsaidDecFormatResolver()

    def process_ref(self, ref: WorkRef) -> None:
        works = list(self.metadata.fetch([ref]))
        if not works:
            return
        work = works[0]
        unsupported = work.extra.setdefault("unsupported_formats", [])
        downloaded: dict[str, bytes] = {}
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
                    "Could not download %s for USAID DEC report #%s: %s",
                    format_name,
                    work.id,
                    exc,
                )
                unsupported.append(format_name)
                continue
            if not is_valid_book_file(content, format_name):
                logger.warning(
                    "USAID DEC report #%s returned an invalid %s file",
                    work.id,
                    format_name.upper(),
                )
                unsupported.append(format_name)
                continue

            media_type = next(
                (
                    book_format.media_type
                    for book_format in work.formats
                    if book_format.name == format_name
                ),
                "application/pdf",
            )
            self.assembler.add_item_for(
                path=archive_name_for(work, format_name),
                content=content,
                mimetype=media_type,
                is_front=False,
            )
            downloaded[format_name] = content
            if cover_image is None:
                cover_image = extract_cover(content, format_name)

        if not downloaded:
            logger.warning(
                "USAID DEC report #%s has no downloadable requested format",
                work.id,
            )
            return

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
