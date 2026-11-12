"""Tests for Bibliothèque numérique romande per-work processing."""

from io import BytesIO
from unittest.mock import MagicMock, patch
from zipfile import ZIP_STORED, ZipFile

from papers2zim.core.models import Cover, Format, Work
from papers2zim.core.ports import WorkRef
from papers2zim.core.progress import ScraperProgress
from papers2zim.core.work_store import WorkStore
from papers2zim.sources.bibliothequenumeriqueromande.catalog import (
    BNR_SOURCE,
    EPUB_MEDIA_TYPE,
)
from papers2zim.sources.bibliothequenumeriqueromande.pipeline import (
    BibliothequeNumeriqueRomandePipeline,
)

WORK_ID = "87a3391f-6bf8-1014-9269-99b4f1e6d0dc"
EPUB_URL = "https://ebooks-bnr.com/opds/fetch.php?data=907&type=epub&id=449"
COVER_URL = "https://ebooks-bnr.com/opds/fetch.php?height=164&id=449"


def _valid_epub() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_STORED) as archive:
        archive.writestr("mimetype", EPUB_MEDIA_TYPE)
    return output.getvalue()


def _work(**overrides) -> Work:
    defaults = {
        "id": WORK_ID,
        "source": BNR_SOURCE,
        "title": "CONTES",
        "cover": Cover(source_url=COVER_URL),
        "formats": [Format(name="epub", media_type=EPUB_MEDIA_TYPE, url=EPUB_URL)],
    }
    defaults.update(overrides)
    return Work(**defaults)


def _pipeline(work: Work, engine: MagicMock, assembler: MagicMock, formats=None):
    metadata = MagicMock()
    metadata.fetch.return_value = [work]
    return BibliothequeNumeriqueRomandePipeline(
        metadata=metadata,
        store=WorkStore(),
        assembler=assembler,
        progress=ScraperProgress(None),
        concurrency=1,
        formats=formats or ["epub"],
        zim_name="test",
        source_slug=BNR_SOURCE,
        display_name="Bibliothèque numérique romande",
        engine=engine,
    )


def test_process_ref_downloads_the_epub_and_stores_the_work():
    work = _work()
    engine = MagicMock()
    engine.fetch_bytes.return_value = _valid_epub()
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with (
        patch(
            "papers2zim.sources.bibliothequenumeriqueromande.pipeline.extract_cover",
            return_value=b"cover bytes",
        ),
        patch(
            "papers2zim.sources.bibliothequenumeriqueromande.pipeline.optimize_epub_bytes",
            return_value=b"optimized epub",
        ),
    ):
        pipeline.process_ref(WorkRef(id=WORK_ID, source=BNR_SOURCE))

    assert pipeline.store.get(BNR_SOURCE, WORK_ID) is work
    assert work.extra["unsupported_formats"] == []
    assert work.extra["has_cover"] is True
    added_paths = [
        call.kwargs["path"] for call in assembler.add_item_for.call_args_list
    ]
    assert sorted(added_paths) == [
        "CONTES.87a3391f-6bf8-1014-9269-99b4f1e6d0dc.epub",
        "covers/87a3391f-6bf8-1014-9269-99b4f1e6d0dc_cover_image.webp",
        "index/book_87a3391f-6bf8-1014-9269-99b4f1e6d0dc",
    ]


def test_process_ref_falls_back_to_the_feed_cover():
    work = _work()
    engine = MagicMock()
    engine.fetch_bytes.return_value = _valid_epub()
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with (
        patch(
            "papers2zim.sources.bibliothequenumeriqueromande.pipeline.extract_cover",
            return_value=None,
        ),
        patch(
            "papers2zim.sources.bibliothequenumeriqueromande.pipeline.fetch_page_cover",
            return_value=b"page cover webp",
        ) as page_cover,
    ):
        pipeline.process_ref(WorkRef(id=WORK_ID, source=BNR_SOURCE))

    page_cover.assert_called_once_with(engine, COVER_URL)
    assembler.add_item_for.assert_any_call(
        path="covers/87a3391f-6bf8-1014-9269-99b4f1e6d0dc_cover_image.webp",
        content=b"page cover webp",
        mimetype="image/webp",
        is_front=False,
    )


def test_process_ref_drops_the_book_when_nothing_downloads():
    work = _work()
    engine = MagicMock()
    engine.fetch_bytes.return_value = b"<!doctype html><html>not a book</html>"
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with patch(
        "papers2zim.sources.bibliothequenumeriqueromande.pipeline.fetch_page_cover"
    ) as cover:
        pipeline.process_ref(WorkRef(id=WORK_ID, source=BNR_SOURCE))

    assert pipeline.store.get(BNR_SOURCE, WORK_ID) is None
    assert work.extra["unsupported_formats"] == ["epub"]
    assembler.add_item_for.assert_not_called()
    cover.assert_not_called()


def test_process_ref_marks_unavailable_requested_formats():
    work = _work()
    engine = MagicMock()
    engine.fetch_bytes.return_value = _valid_epub()
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler, formats=["epub", "pdf"])

    with patch(
        "papers2zim.sources.bibliothequenumeriqueromande.pipeline.extract_cover",
        return_value=b"cover",
    ):
        pipeline.process_ref(WorkRef(id=WORK_ID, source=BNR_SOURCE))

    assert work.extra["unsupported_formats"] == ["pdf"]


def _author_pipeline():
    return BibliothequeNumeriqueRomandePipeline(
        metadata=MagicMock(),
        store=WorkStore(),
        assembler=MagicMock(),
        progress=ScraperProgress(None),
        concurrency=1,
        formats=["epub"],
        zim_name="test",
        source_slug=BNR_SOURCE,
        display_name="Bibliothèque numérique romande",
        engine=MagicMock(),
        with_author_bio=True,
        with_author_portrait=True,
        requested_languages=["fr"],
    )


def test_enrich_authors_is_skipped_without_author_details():
    pipeline = _author_pipeline()
    pipeline.with_author_bio = False
    pipeline.with_author_portrait = False

    with patch(
        "papers2zim.sources.bibliothequenumeriqueromande.pipeline."
        "BibliothequeNumeriqueRomandeAuthorEnricher"
    ) as enricher_cls:
        pipeline.enrich_authors()

    enricher_cls.assert_not_called()


def test_enrich_authors_builds_the_bnr_article_enricher():
    pipeline = _author_pipeline()

    with patch(
        "papers2zim.sources.bibliothequenumeriqueromande.pipeline."
        "BibliothequeNumeriqueRomandeAuthorEnricher"
    ) as enricher_cls:
        pipeline.enrich_authors()

    kwargs = enricher_cls.call_args.kwargs
    assert kwargs["with_bio"] is True
    assert kwargs["with_portrait"] is True
    assert kwargs["concurrency"] == 1
    assert kwargs["language"] == "fr"
    enricher_cls.return_value.enrich_authors.assert_called_once_with(pipeline.store)
