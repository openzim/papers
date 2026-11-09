"""Tests for USAID DEC Archive per-work processing."""

from unittest.mock import MagicMock, patch

import requests

from papers2zim.core.models import Format, Work
from papers2zim.core.ports import WorkRef
from papers2zim.core.progress import ScraperProgress
from papers2zim.core.work_store import WorkStore
from papers2zim.sources.usaiddec.pipeline import UsaidDecPipeline


def _work(**overrides) -> Work:
    defaults = {
        "id": "PA00JMRT",
        "source": "usaiddec",
        "title": "Evaluation report",
        "formats": [
            Format(
                name="pdf",
                media_type="application/pdf",
                url="https://docs.aiddata.org/ad4/pdfs/usaid-archive/PA00JMRT.pdf",
            )
        ],
    }
    defaults.update(overrides)
    return Work(**defaults)


def _pipeline(
    work: Work, engine: MagicMock, assembler: MagicMock, formats=None, works=None
):
    metadata = MagicMock()
    metadata.fetch.return_value = [work] if works is None else works
    return UsaidDecPipeline(
        metadata=metadata,
        store=WorkStore(),
        assembler=assembler,
        progress=ScraperProgress(None),
        concurrency=1,
        formats=formats or ["pdf"],
        zim_name="test",
        source_slug="usaiddec",
        display_name="USAID DEC Archive",
        engine=engine,
    )


def test_process_ref_downloads_pdf_and_stores_the_work():
    work = _work()
    engine = MagicMock()
    engine.fetch_bytes.return_value = b"%PDF-1.7 pdf bytes"
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with patch(
        "papers2zim.sources.usaiddec.pipeline.extract_cover",
        return_value=None,
    ):
        pipeline.process_ref(WorkRef(id="PA00JMRT", source="usaiddec"))

    assert pipeline.store.get("usaiddec", "PA00JMRT") is work
    assert work.extra["unsupported_formats"] == []
    assert work.extra["has_cover"] is False
    added_paths = [
        call.kwargs["path"] for call in assembler.add_item_for.call_args_list
    ]
    assert "Evaluation report.PA00JMRT.pdf" in added_paths


def test_process_ref_drops_report_when_pdf_is_invalid():
    work = _work()
    engine = MagicMock()
    engine.fetch_bytes.return_value = b"not a pdf"
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with patch(
        "papers2zim.sources.usaiddec.pipeline.is_valid_book_file",
        return_value=False,
    ):
        pipeline.process_ref(WorkRef(id="PA00JMRT", source="usaiddec"))

    assert pipeline.store.get("usaiddec", "PA00JMRT") is None
    assert work.extra["unsupported_formats"] == ["pdf"]
    assembler.add_item_for.assert_not_called()


def test_process_ref_marks_unavailable_unsupported_formats():
    work = _work(formats=[])
    engine = MagicMock()
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler, formats=["epub", "pdf"])

    pipeline.process_ref(WorkRef(id="PA00JMRT", source="usaiddec"))

    assert sorted(work.extra["unsupported_formats"]) == ["epub", "pdf"]
    assembler.add_item_for.assert_not_called()


def test_process_ref_without_metadata_stores_nothing():
    engine = MagicMock()
    assembler = MagicMock()
    pipeline = _pipeline(_work(), engine, assembler, works=[])

    pipeline.process_ref(WorkRef(id="PA00JMRT", source="usaiddec"))

    assembler.add_item_for.assert_not_called()
    assert pipeline.store.get("usaiddec", "PA00JMRT") is None


def test_process_ref_drops_the_report_when_the_download_fails():
    work = _work()
    engine = MagicMock()
    engine.fetch_bytes.side_effect = requests.ConnectionError("connection reset")
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    pipeline.process_ref(WorkRef(id="PA00JMRT", source="usaiddec"))

    assert work.extra["unsupported_formats"] == ["pdf"]
    assembler.add_item_for.assert_not_called()
    assert pipeline.store.get("usaiddec", "PA00JMRT") is None


def test_process_ref_gives_up_on_a_client_error():
    work = _work()
    response = requests.Response()
    response.status_code = 404
    engine = MagicMock()
    engine.fetch_bytes.side_effect = requests.HTTPError(response=response)
    pipeline = _pipeline(work, engine, MagicMock())

    pipeline.process_ref(WorkRef(id="PA00JMRT", source="usaiddec"))

    assert work.extra["unsupported_formats"] == ["pdf"]
    assert pipeline.store.get("usaiddec", "PA00JMRT") is None


def test_process_ref_adds_the_extracted_cover():
    work = _work()
    engine = MagicMock()
    engine.fetch_bytes.return_value = b"%PDF-1.7 pdf bytes"
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with patch(
        "papers2zim.sources.usaiddec.pipeline.extract_cover",
        return_value=b"webp bytes",
    ):
        pipeline.process_ref(WorkRef(id="PA00JMRT", source="usaiddec"))

    added = {
        call.kwargs["path"]: call.kwargs["content"]
        for call in assembler.add_item_for.call_args_list
    }
    assert added["covers/PA00JMRT_cover_image.webp"] == b"webp bytes"
    assert work.extra["has_cover"] is True
    assert work.cover is not None
    assert pipeline.store.get("usaiddec", "PA00JMRT") is work
