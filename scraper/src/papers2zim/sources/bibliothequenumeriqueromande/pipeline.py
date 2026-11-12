"""Per-work processing for Bibliothèque numérique romande.

Each book is downloaded from its OPDS acquisition link in the requested binary
formats (EPUB only), validated, optimized and added to the ZIM together with a
cover extracted from the book file or, failing that, the thumbnail advertised in
the feed. Formats BNR does not serve for a work are recorded as unsupported,
mirroring the other sources' drop-format behavior.
"""

import requests

from papers2zim.constants import logger
from papers2zim.core.author_enrichment import zim_language
from papers2zim.core.content_validation import is_html_document, is_valid_book_file
from papers2zim.core.covers import extract_cover
from papers2zim.core.download_engine import DownloadEngine, is_fatal_http_error
from papers2zim.core.epub_optimizer import optimize_epub_bytes
from papers2zim.core.models import Cover, Work
from papers2zim.core.pipeline import Pipeline
from papers2zim.core.ports import WorkRef
from papers2zim.core.utils import archive_name_for
from papers2zim.sources.bibliothequenumeriqueromande.author_enricher import (
    BibliothequeNumeriqueRomandeAuthorEnricher,
)
from papers2zim.sources.bibliothequenumeriqueromande.catalog import EPUB_MEDIA_TYPE
from papers2zim.sources.bibliothequenumeriqueromande.covers import fetch_page_cover
from papers2zim.sources.bibliothequenumeriqueromande.resolver import (
    BibliothequeNumeriqueRomandeFormatResolver,
)


class BibliothequeNumeriqueRomandePipeline(Pipeline):
    """Download BNR EPUB editions and expose them to the UI readers."""

    def __init__(
        self,
        *,
        engine: DownloadEngine,
        with_author_bio: bool = False,
        with_author_portrait: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.engine = engine
        self.with_author_bio = with_author_bio
        self.with_author_portrait = with_author_portrait
        self.resolver = BibliothequeNumeriqueRomandeFormatResolver()

    def enrich_authors(self) -> None:
        """Fetch a biography and portrait for each author when requested."""
        if not self.with_author_bio and not self.with_author_portrait:
            return
        enricher = BibliothequeNumeriqueRomandeAuthorEnricher(
            self.engine,
            self.assembler,
            with_bio=self.with_author_bio,
            with_portrait=self.with_author_portrait,
            concurrency=self.concurrency,
            language=zim_language(self.requested_languages),
        )
        enricher.enrich_authors(self.store)

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
                cover_image = extract_cover(content, format_name, declared_only=True)

        if not contents:
            logger.warning(
                "Bibliothèque numérique romande book %s has no downloadable "
                "requested format",
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
                "Could not download %s for Bibliothèque numérique romande book %s: %s",
                format_name,
                work.id,
                exc,
            )
            unsupported.append(format_name)
            return None

        if is_html_document(content) or not is_valid_book_file(content, format_name):
            logger.warning(
                "Bibliothèque numérique romande book %s returned an invalid "
                "%s response: %s",
                work.id,
                format_name.upper(),
                request.url,
            )
            unsupported.append(format_name)
            return None

        if format_name == "epub":
            content = optimize_epub_bytes(
                content,
                log_context=f"Bibliothèque numérique romande book {work.id}",
            )

        self.assembler.add_item_for(
            path=archive_name_for(work, format_name),
            content=content,
            mimetype=next(
                (
                    book_format.media_type
                    for book_format in work.formats
                    if book_format.name == format_name
                ),
                EPUB_MEDIA_TYPE,
            ),
            is_front=False,
        )
        return content
