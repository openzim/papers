"""Per-work processing for Wikisource.

Each work is downloaded from ws-export in the requested binary formats (epub in
practice), validated, and added to the ZIM together with a cover extracted from
the book file. Formats ws-export does not serve for a given work are recorded as
unsupported, mirroring the other sources' drop-format behavior.
"""

import requests

from papers2zim.constants import logger
from papers2zim.core.content_validation import is_html_document, is_valid_book_file
from papers2zim.core.covers import extract_cover
from papers2zim.core.download_engine import DownloadEngine, is_fatal_http_error
from papers2zim.core.exporters.html_reader_controls import (
    export_html_reader_control_assets,
)
from papers2zim.core.models import Cover, Work
from papers2zim.core.pipeline import Pipeline
from papers2zim.core.ports import WorkRef
from papers2zim.core.utils import archive_name_for
from papers2zim.sources.wikisource.description import enrich_work_descriptions
from papers2zim.sources.wikisource.html_export import HtmlEdition, extract_html_edition
from papers2zim.sources.wikisource.resolver import WikisourceFormatResolver


class WikisourcePipeline(Pipeline):
    """Download ws-export editions and add them to the ZIM."""

    def __init__(self, *, engine: DownloadEngine, **kwargs):
        super().__init__(**kwargs)
        self.engine = engine
        self.resolver = WikisourceFormatResolver()

    def run(self, refs: list[WorkRef]) -> None:
        if "html" in self.formats:
            export_html_reader_control_assets(self.assembler)
        super().run(refs)

    def enrich_descriptions(self) -> None:
        """Fill in missing book descriptions from Wikidata."""
        enrich_work_descriptions(self.store, self.engine)

    def process_ref(self, ref: WorkRef) -> None:
        works = list(self.metadata.fetch([ref]))
        if not works:
            return
        work = works[0]
        unsupported = work.extra.setdefault("unsupported_formats", [])

        contents: dict[str, bytes] = {}
        cover_image: bytes | None = None
        for format_name in self.formats:
            if format_name == "html":
                continue
            content = self._download_format(work, format_name, unsupported)
            if content is None:
                continue
            contents[format_name] = content
            if cover_image is None:
                # Only extract declared covers so books without a cover fall back
                # to the placeholder rather than picking up the site logo.
                cover_image = extract_cover(content, format_name, declared_only=True)

        if "html" in self.formats:
            edition = self._download_html(work, unsupported, list(contents))
            if edition is not None:
                for path, (content, mimetype) in edition.pages.items():
                    self.assembler.add_item_for(
                        path=path,
                        content=content,
                        mimetype=mimetype,
                        is_front=False,
                    )
                contents["html"] = edition.pages[edition.index_path][0]

        if not contents:
            logger.warning(
                "Wikisource book %s has no downloadable requested format", work.id
            )
            return

        if cover_image:
            self.assembler.add_item_for(
                path=f"covers/{work.id}_cover_image.webp",
                content=cover_image,
                mimetype="image/webp",
                is_front=False,
            )
            work.cover = Cover()
            work.extra["has_cover"] = True
        self.store.add(work)
        self.add_book_search_item(work, contents)

    def _download_html(
        self, work: Work, unsupported: list[str], formats: list[str]
    ) -> HtmlEdition | None:
        request = self.resolver.resolve(work, "html")
        if request is None:
            unsupported.append("html")
            return None
        try:
            content = self.engine.fetch_bytes(request.url)
        except requests.RequestException as exc:
            log = logger.debug if is_fatal_http_error(exc) else logger.warning
            log("Could not download HTML for %s: %s", work.id, exc)
            unsupported.append("html")
            return None

        edition = extract_html_edition(content, work, formats)
        if edition is None:
            logger.warning(
                "Wikisource book %s returned an invalid HTML archive: %s",
                work.id,
                request.url,
            )
            unsupported.append("html")
        return edition

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
            log("Could not download %s for %s: %s", format_name, work.id, exc)
            unsupported.append(format_name)
            return None

        if is_html_document(content) or not is_valid_book_file(content, format_name):
            logger.warning(
                "Wikisource book %s returned an invalid %s response: %s",
                work.id,
                format_name.upper(),
                request.url,
            )
            unsupported.append(format_name)
            return None

        self.assembler.add_item_for(
            path=archive_name_for(work, format_name),
            content=content,
            mimetype=next(
                (fmt.media_type for fmt in work.formats if fmt.name == format_name),
                "application/octet-stream",
            ),
            is_front=False,
        )
        return content
