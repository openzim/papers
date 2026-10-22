"""Tests for One More Library per-work processing."""

from io import BytesIO
from unittest.mock import MagicMock, patch
from zipfile import ZIP_STORED, ZipFile

from papers2zim.core.models import Cover, Format, Work
from papers2zim.core.ports import WorkRef
from papers2zim.core.progress import ScraperProgress
from papers2zim.core.work_store import WorkStore
from papers2zim.sources.onemorelibrary.pipeline import OnemorelibraryPipeline


def _valid_epub() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_STORED) as archive:
        archive.writestr("mimetype", "application/epub+zip")
    return output.getvalue()


def _work(**overrides) -> Work:
    defaults = {
        "id": "2833",
        "source": "onemorelibrary",
        "title": "On Beauty",
        "cover": Cover(source_url="https://onemorelibrary.com/cover.png"),
        "formats": [
            Format(
                name="pdf",
                media_type="application/pdf",
                url="https://onemorelibrary.com/download?fid=14598",
            ),
            Format(
                name="epub",
                media_type="application/epub+zip",
                url="https://onemorelibrary.com/download?fid=14599",
            ),
        ],
    }
    defaults.update(overrides)
    return Work(**defaults)


def _pipeline(work: Work, engine: MagicMock, assembler: MagicMock, formats=None):
    metadata = MagicMock()
    metadata.fetch.return_value = [work]
    return OnemorelibraryPipeline(
        metadata=metadata,
        store=WorkStore(),
        assembler=assembler,
        progress=ScraperProgress(None),
        concurrency=1,
        formats=formats or ["epub", "pdf"],
        zim_name="test",
        source_slug="onemorelibrary",
        display_name="One More Library",
        engine=engine,
    )


def test_process_ref_downloads_pdf_and_epub_and_stores_the_work():
    work = _work()
    engine = MagicMock()
    engine.fetch_bytes.side_effect = {
        "https://onemorelibrary.com/download?fid=14598": b"%PDF-1.7 pdf bytes",
        "https://onemorelibrary.com/download?fid=14599": _valid_epub(),
    }.get
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with (
        patch(
            "papers2zim.sources.onemorelibrary.pipeline.extract_cover",
            return_value=b"cover bytes",
        ),
        patch(
            "papers2zim.sources.onemorelibrary.pipeline.optimize_epub_bytes",
            return_value=b"optimized epub",
        ),
    ):
        pipeline.process_ref(WorkRef(id="2833", source="onemorelibrary"))

    assert pipeline.store.get("onemorelibrary", "2833") is work
    assert work.extra["unsupported_formats"] == []
    assert work.extra["has_cover"] is True
    added_paths = [
        call.kwargs["path"] for call in assembler.add_item_for.call_args_list
    ]
    assert sorted(added_paths) == [
        "On Beauty.2833.epub",
        "On Beauty.2833.pdf",
        "covers/2833_cover_image.webp",
    ]


def test_process_ref_falls_back_to_the_page_cover():
    work = _work(
        formats=[
            Format(
                name="pdf",
                media_type="application/pdf",
                url="https://onemorelibrary.com/download?fid=14598",
            )
        ]
    )
    engine = MagicMock()
    engine.fetch_bytes.side_effect = [
        b"%PDF-1.7 pdf bytes",
        b"page cover bytes",
    ]
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler, formats=["pdf"])

    with (
        patch(
            "papers2zim.sources.onemorelibrary.pipeline.extract_cover",
            return_value=None,
        ),
        patch(
            "papers2zim.sources.onemorelibrary.pipeline.fetch_page_cover",
            return_value=b"page cover webp",
        ) as page_cover,
    ):
        pipeline.process_ref(WorkRef(id="2833", source="onemorelibrary"))

    page_cover.assert_called_once_with(engine, "https://onemorelibrary.com/cover.png")
    assembler.add_item_for.assert_any_call(
        path="covers/2833_cover_image.webp",
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

    with (
        patch("papers2zim.sources.onemorelibrary.pipeline.fetch_page_cover") as cover,
    ):
        pipeline.process_ref(WorkRef(id="2833", source="onemorelibrary"))

    assert pipeline.store.get("onemorelibrary", "2833") is None
    assert work.extra["unsupported_formats"] == ["epub", "pdf"]
    assembler.add_item_for.assert_not_called()
    cover.assert_not_called()


def test_process_ref_marks_unavailable_unsupported_formats():
    work = _work(
        formats=[
            Format(
                name="pdf",
                media_type="application/pdf",
                url="https://onemorelibrary.com/download?fid=14598",
            )
        ]
    )
    engine = MagicMock()
    engine.fetch_bytes.return_value = b"%PDF-1.7 pdf bytes"
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler, formats=["epub", "pdf", "html"])

    with patch(
        "papers2zim.sources.onemorelibrary.pipeline.extract_cover",
        return_value=b"cover",
    ):
        pipeline.process_ref(WorkRef(id="2833", source="onemorelibrary"))

    assert sorted(work.extra["unsupported_formats"]) == ["epub", "html"]
