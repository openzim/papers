"""Gutenberg `Pipeline` implementation.

Supplies the source-specific hooks of `core.pipeline.Pipeline`:
- `setup()`: export the infobox CSS/JS/icon assets first, to fail fast,
- `process_ref()`: fetch metadata through the `MetadataPort`, download the
  book in-memory with `download_book` through the shared `DownloadEngine`
  and export it with `export_book`. HTML rewriting still calls
  `update_html_for_static` inside `export_book` (see `GutenbergHtmlRewriter`'s
  docstring for why the port is not used there yet).
"""

from dataclasses import replace as dataclass_replace

from papers2zim.constants import logger
from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.exporters.html_reader_controls import (
    export_html_reader_control_assets,
)
from papers2zim.core.models import CollectionRef
from papers2zim.core.pipeline import Pipeline
from papers2zim.core.ports import WorkRef
from papers2zim.sources.gutenberg.author_enricher import enrich_authors
from papers2zim.sources.gutenberg.catalog import (
    LCC_SHELF_KIND,
    collapse_literature_shelf,
)
from papers2zim.sources.gutenberg.downloader import download_book
from papers2zim.sources.gutenberg.exporter import export_book


def _simplify_literature_shelf(collection: CollectionRef) -> CollectionRef:
    """Collapse a literature sub-shelf collection down to the general "P" one"""
    if collection.kind != LCC_SHELF_KIND:
        return collection
    shelf = collapse_literature_shelf(collection.id)
    if shelf == collection.id:
        return collection
    return dataclass_replace(collection, id=shelf, name=shelf)


class GutenbergPipeline(Pipeline):
    """Per-book pipeline for the Gutenberg source, wired through ports"""

    def __init__(
        self,
        *,
        engine: DownloadEngine,
        mirror_url: str,
        with_author_bio: bool = False,
        with_author_portrait: bool = False,
        languages: list[str] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.engine = engine
        self.mirror_url = mirror_url
        self.with_author_bio = with_author_bio
        self.with_author_portrait = with_author_portrait
        # Splitting the "P" (language and literature) shelf by language/
        # nationality sub-class (English, French, ...) isn't useful when the
        # whole ZIM is already restricted to a single language.
        self.single_language = len(languages or []) == 1

    def setup(self) -> None:
        # Export shared reader-control assets first to fail fast if any are missing.
        logger.info("Exporting HTML reader controls")
        export_html_reader_control_assets(self.assembler)

    def enrich_authors(self) -> None:
        """Fetch a biography and portrait for each author when requested."""
        if not self.with_author_bio and not self.with_author_portrait:
            return
        enrich_authors(
            self.store,
            self.engine,
            self.assembler,
            with_bio=self.with_author_bio,
            with_portrait=self.with_author_portrait,
            concurrency=self.concurrency,
        )

    def process_ref(self, ref: WorkRef) -> None:
        """Fetch metadata, download book content and export directly to ZIM"""
        works = list(self.metadata.fetch([ref]))
        if not works:
            return
        work = works[0]
        if self.single_language:
            work.collections = [
                _simplify_literature_shelf(collection)
                for collection in work.collections
            ]
        self.store.add(work)

        book_content = download_book(
            mirror_url=self.mirror_url,
            work=work,
            formats=self.formats,
            work_store=self.store,
            engine=self.engine,
        )

        if book_content:
            export_book(
                work=work,
                book_files=book_content.files,
                formats=self.formats,
                mirror_url=self.mirror_url,
                assembler=self.assembler,
                engine=self.engine,
                _zim_name=self.zim_name,
                _title_search=self.title_search,
            )
