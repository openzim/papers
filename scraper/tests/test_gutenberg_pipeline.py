"""Tests for Gutenberg per-work processing, notably LCC shelf collapsing."""

from unittest.mock import MagicMock, patch

import pytest

from papers2zim.core.models import CollectionRef, Work
from papers2zim.core.ports import WorkRef
from papers2zim.core.progress import ScraperProgress
from papers2zim.core.work_store import WorkStore
from papers2zim.sources.gutenberg.catalog import LCC_SHELF_KIND
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

    with patch("papers2zim.sources.gutenberg.pipeline.enrich_authors") as enrich:
        pipeline.enrich_authors()

    assert enrich.call_args.kwargs["language"] == expected


def test_enrich_authors_is_skipped_without_author_details():
    pipeline = _author_pipeline(["fr"])
    pipeline.with_author_bio = False
    pipeline.with_author_portrait = False

    with patch("papers2zim.sources.gutenberg.pipeline.enrich_authors") as enrich:
        pipeline.enrich_authors()

    enrich.assert_not_called()


@pytest.mark.parametrize(
    ("with_bio", "with_portrait"),
    [(True, True), (True, False), (False, True)],
)
def test_enrich_authors_forwards_both_flags_and_language(with_bio, with_portrait):
    pipeline = _author_pipeline(["fr"])
    pipeline.with_author_bio = with_bio
    pipeline.with_author_portrait = with_portrait

    with patch("papers2zim.sources.gutenberg.pipeline.enrich_authors") as enrich:
        pipeline.enrich_authors()

    kwargs = enrich.call_args.kwargs
    assert kwargs["with_bio"] is with_bio
    assert kwargs["with_portrait"] is with_portrait
    assert kwargs["language"] == "fr"
