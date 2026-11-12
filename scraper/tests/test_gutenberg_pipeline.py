"""Tests for Gutenberg per-work processing, notably LCC shelf collapsing."""

from unittest.mock import MagicMock, patch

import pytest

from papers2zim.core.models import CollectionRef, Work
from papers2zim.core.ports import WorkRef
from papers2zim.core.progress import ScraperProgress
from papers2zim.core.work_store import WorkStore
from papers2zim.sources.gutenberg.catalog import LCC_SHELF_KIND
from papers2zim.sources.gutenberg.downloader import BookContent
from papers2zim.sources.gutenberg.pipeline import GutenbergPipeline


def _pipeline(work: Work, *, languages: list[str] | None) -> GutenbergPipeline:
    metadata = MagicMock()
    metadata.fetch.return_value = [work]
    return GutenbergPipeline(
        metadata=metadata,
        store=WorkStore(),
        assembler=MagicMock(),
        progress=ScraperProgress(None),
        concurrency=1,
        formats=["epub"],
        zim_name="test",
        source_slug="gutenberg",
        display_name="Project Gutenberg",
        title_search=False,
        engine=MagicMock(),
        mirror_url="https://example.org",
        languages=languages,
    )


def _work_with_shelf(shelf: str) -> Work:
    return Work(
        id="84",
        source="gutenberg",
        title="Frankenstein",
        collections=[CollectionRef(id=shelf, name=shelf, kind=LCC_SHELF_KIND)],
    )


def test_single_language_zim_collapses_literature_sub_shelf():
    work = _work_with_shelf("PR")
    pipeline = _pipeline(work, languages=["en"])

    with patch(
        "papers2zim.sources.gutenberg.pipeline.download_book", return_value=None
    ):
        pipeline.process_ref(WorkRef(id="84", source="gutenberg"))

    stored = pipeline.store.get("gutenberg", "84")
    assert stored is not None
    assert stored.collections == [CollectionRef(id="P", name="P", kind=LCC_SHELF_KIND)]


def test_multi_language_zim_keeps_literature_sub_shelf():
    work = _work_with_shelf("PR")
    pipeline = _pipeline(work, languages=["en", "fr"])

    with patch(
        "papers2zim.sources.gutenberg.pipeline.download_book", return_value=None
    ):
        pipeline.process_ref(WorkRef(id="84", source="gutenberg"))

    stored = pipeline.store.get("gutenberg", "84")
    assert stored is not None
    assert stored.collections == [
        CollectionRef(id="PR", name="PR", kind=LCC_SHELF_KIND)
    ]


def test_single_language_zim_leaves_non_literature_shelf_untouched():
    work = _work_with_shelf("CDEF")
    pipeline = _pipeline(work, languages=["en"])

    with patch(
        "papers2zim.sources.gutenberg.pipeline.download_book", return_value=None
    ):
        pipeline.process_ref(WorkRef(id="84", source="gutenberg"))

    stored = pipeline.store.get("gutenberg", "84")
    assert stored is not None
    assert stored.collections == [
        CollectionRef(id="CDEF", name="CDEF", kind=LCC_SHELF_KIND)
    ]


def _author_pipeline(requested_languages: list[str] | None) -> GutenbergPipeline:
    metadata = MagicMock()
    pipeline = GutenbergPipeline(
        metadata=metadata,
        store=WorkStore(),
        assembler=MagicMock(),
        progress=ScraperProgress(None),
        concurrency=1,
        formats=["epub"],
        zim_name="test",
        source_slug="gutenberg",
        display_name="Project Gutenberg",
        title_search=False,
        engine=MagicMock(),
        mirror_url="https://example.org",
        with_author_bio=True,
        with_author_portrait=True,
        requested_languages=requested_languages,
    )
    return pipeline


@pytest.mark.parametrize(
    ("requested_languages", "expected"),
    [(["fr"], "fr"), (["fra"], "fr"), (["fr", "en"], None), (None, None)],
)
def test_enrich_authors_receives_the_single_zim_language(requested_languages, expected):
    pipeline = _author_pipeline(requested_languages)

    with patch(
        "papers2zim.sources.gutenberg.pipeline.GutenbergAuthorEnricher"
    ) as enricher_cls:
        pipeline.enrich_authors()

    assert enricher_cls.call_args.kwargs["language"] == expected
    enricher_cls.return_value.enrich_authors.assert_called_once_with(pipeline.store)


def test_enrich_authors_is_skipped_without_author_details():
    pipeline = _author_pipeline(["fr"])
    pipeline.with_author_bio = False
    pipeline.with_author_portrait = False

    with patch(
        "papers2zim.sources.gutenberg.pipeline.GutenbergAuthorEnricher"
    ) as enricher_cls:
        pipeline.enrich_authors()

    enricher_cls.assert_not_called()


@pytest.mark.parametrize(
    ("with_bio", "with_portrait"),
    [(True, True), (True, False), (False, True)],
)
def test_enrich_authors_forwards_both_flags_and_language(with_bio, with_portrait):
    pipeline = _author_pipeline(["fr"])
    pipeline.with_author_bio = with_bio
    pipeline.with_author_portrait = with_portrait

    with patch(
        "papers2zim.sources.gutenberg.pipeline.GutenbergAuthorEnricher"
    ) as enricher_cls:
        pipeline.enrich_authors()

    kwargs = enricher_cls.call_args.kwargs
    assert kwargs["with_bio"] is with_bio
    assert kwargs["with_portrait"] is with_portrait
    assert kwargs["language"] == "fr"
    enricher_cls.return_value.enrich_authors.assert_called_once_with(pipeline.store)


def _process_with_files(
    work: Work, files: dict[str, bytes], formats: list[str]
) -> MagicMock:
    """Process a work whose download returns `files`; the search item mock"""
    pipeline = _pipeline(work, languages=None)
    pipeline.formats = formats
    with (
        patch(
            "papers2zim.sources.gutenberg.pipeline.download_book",
            return_value=BookContent(work=work, files=files),
        ),
        patch("papers2zim.sources.gutenberg.pipeline.export_book"),
        patch.object(pipeline, "add_book_search_item") as add_search_item,
    ):
        pipeline.process_ref(WorkRef(id=work.id, source="gutenberg"))
    return add_search_item


def test_process_ref_indexes_the_book_files_but_not_companions():
    work = _work_with_shelf("PR")
    files = {
        "84.html": b"<p>main</p>",
        "84.epub": b"epub bytes",
        "84.pdf": b"pdf bytes",
        "84_chapter2.html": b"<p>companion</p>",
        "84_cover.jpg": b"jpg",
    }

    add_search_item = _process_with_files(work, files, ["epub", "html"])

    add_search_item.assert_called_once_with(
        work, {"html": b"<p>main</p>", "epub": b"epub bytes"}
    )


def test_process_ref_indexes_only_requested_formats():
    work = _work_with_shelf("PR")
    files = {"84.html": b"<p>main</p>", "84.epub": b"epub bytes"}

    add_search_item = _process_with_files(work, files, ["epub"])

    add_search_item.assert_called_once_with(work, {"epub": b"epub bytes"})


def test_process_ref_does_not_index_a_book_that_failed_to_download():
    work = _work_with_shelf("PR")
    pipeline = _pipeline(work, languages=None)
    with (
        patch("papers2zim.sources.gutenberg.pipeline.download_book", return_value=None),
        patch.object(pipeline, "add_book_search_item") as add_search_item,
    ):
        pipeline.process_ref(WorkRef(id="84", source="gutenberg"))
    add_search_item.assert_not_called()
