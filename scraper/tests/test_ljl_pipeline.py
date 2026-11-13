"""Tests for Littérature jeunesse libre per-work processing."""

from io import BytesIO
from unittest.mock import MagicMock, patch
from zipfile import ZIP_STORED, ZipFile

from papers2zim.core.models import Cover, Format, Work
from papers2zim.core.ports import WorkRef
from papers2zim.core.progress import ScraperProgress
from papers2zim.core.work_store import WorkStore
from papers2zim.sources.litteraturejeunesselibre.catalog import (
    EPUB_MEDIA_TYPE,
    LJL_SOURCE,
    PDF_MEDIA_TYPE,
)
from papers2zim.sources.litteraturejeunesselibre.pipeline import (
    LitteratureJeunesseLibrePipeline,
)

WORK_ID = "87a3391f-6bf8-1014-9269-99b4f1e6d0dc"
EPUB_URL = "https://litterature-jeunesse-libre.fr/bbs/opds/fetch.php?data=907&type=epub"
PDF_URL = "https://litterature-jeunesse-libre.fr/bbs/opds/fetch.php?data=907&type=pdf"
COVER_URL = "https://litterature-jeunesse-libre.fr/bbs/opds/fetch.php?height=164"


def _valid_epub() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_STORED) as archive:
        archive.writestr("mimetype", EPUB_MEDIA_TYPE)
    return output.getvalue()


def _valid_pdf() -> bytes:
    return b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"


def _work(**overrides) -> Work:
    defaults = {
        "id": WORK_ID,
        "source": LJL_SOURCE,
        "title": "Animaux",
        "cover": Cover(source_url=COVER_URL),
        "formats": [
            Format(name="epub", media_type=EPUB_MEDIA_TYPE, url=EPUB_URL),
            Format(name="pdf", media_type=PDF_MEDIA_TYPE, url=PDF_URL),
        ],
    }
    defaults.update(overrides)
    return Work(**defaults)


def _pipeline(work: Work, engine: MagicMock, assembler: MagicMock, formats=None):
    metadata = MagicMock()
    metadata.fetch.return_value = [work]
    return LitteratureJeunesseLibrePipeline(
        metadata=metadata,
        store=WorkStore(),
        assembler=assembler,
        progress=ScraperProgress(None),
        concurrency=1,
        formats=formats or ["epub"],
        zim_name="test",
        source_slug=LJL_SOURCE,
        display_name="Littérature jeunesse libre",
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
            "papers2zim.sources.litteraturejeunesselibre.pipeline.extract_cover",
            return_value=b"cover bytes",
        ),
        patch(
            "papers2zim.sources.litteraturejeunesselibre.pipeline.optimize_epub_bytes",
            return_value=b"optimized epub",
        ),
    ):
        pipeline.process_ref(WorkRef(id=WORK_ID, source=LJL_SOURCE))

    assert pipeline.store.get(LJL_SOURCE, WORK_ID) is work
    assert work.extra["unsupported_formats"] == []
    assert work.extra["has_cover"] is True
    added_paths = [
        call.kwargs["path"] for call in assembler.add_item_for.call_args_list
    ]
    assert sorted(added_paths) == [
        "Animaux.87a3391f-6bf8-1014-9269-99b4f1e6d0dc.epub",
        "covers/87a3391f-6bf8-1014-9269-99b4f1e6d0dc_cover_image.webp",
        "index/book_87a3391f-6bf8-1014-9269-99b4f1e6d0dc",
    ]


def test_process_ref_downloads_every_requested_format():
    work = _work()
    engine = MagicMock()
    engine.fetch_bytes.side_effect = lambda url: (
        _valid_epub() if url == EPUB_URL else _valid_pdf()
    )
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler, formats=["epub", "pdf"])

    with (
        patch(
            "papers2zim.sources.litteraturejeunesselibre.pipeline.extract_cover",
            return_value=b"cover",
        ),
        patch(
            "papers2zim.sources.litteraturejeunesselibre.pipeline.optimize_epub_bytes",
            return_value=b"optimized epub",
        ),
    ):
        pipeline.process_ref(WorkRef(id=WORK_ID, source=LJL_SOURCE))

    assert work.extra["unsupported_formats"] == []
    mimetypes = {
        call.kwargs["path"]: call.kwargs["mimetype"]
        for call in assembler.add_item_for.call_args_list
    }
    assert mimetypes["Animaux.87a3391f-6bf8-1014-9269-99b4f1e6d0dc.epub"] == (
        EPUB_MEDIA_TYPE
    )
    assert mimetypes["Animaux.87a3391f-6bf8-1014-9269-99b4f1e6d0dc.pdf"] == (
        PDF_MEDIA_TYPE
    )


def test_process_ref_falls_back_to_the_feed_cover():
    work = _work()
    engine = MagicMock()
    engine.fetch_bytes.return_value = _valid_epub()
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with (
        patch(
            "papers2zim.sources.litteraturejeunesselibre.pipeline.extract_cover",
            return_value=None,
        ),
        patch(
            "papers2zim.sources.litteraturejeunesselibre.pipeline.fetch_page_cover",
            return_value=b"page cover webp",
        ) as page_cover,
    ):
        pipeline.process_ref(WorkRef(id=WORK_ID, source=LJL_SOURCE))

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
        "papers2zim.sources.litteraturejeunesselibre.pipeline.fetch_page_cover"
    ) as cover:
        pipeline.process_ref(WorkRef(id=WORK_ID, source=LJL_SOURCE))

    assert pipeline.store.get(LJL_SOURCE, WORK_ID) is None
    assert work.extra["unsupported_formats"] == ["epub"]
    assembler.add_item_for.assert_not_called()
    cover.assert_not_called()


def test_process_ref_marks_unavailable_requested_formats():
    work = _work()
    engine = MagicMock()
    engine.fetch_bytes.return_value = _valid_epub()
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler, formats=["epub", "html"])

    with patch(
        "papers2zim.sources.litteraturejeunesselibre.pipeline.extract_cover",
        return_value=b"cover",
    ):
        pipeline.process_ref(WorkRef(id=WORK_ID, source=LJL_SOURCE))

    assert work.extra["unsupported_formats"] == ["html"]
