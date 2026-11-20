"""Tests for Wikisource per-work processing."""

from io import BytesIO
from unittest.mock import MagicMock, patch
from zipfile import ZIP_STORED, ZipFile

import pytest
import requests

from papers2zim.constants import DEFAULT_HTTP_TIMEOUT
from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.models import Format, Work
from papers2zim.core.ports import WorkRef
from papers2zim.core.progress import ScraperProgress
from papers2zim.core.work_store import WorkStore
from papers2zim.sources.wikisource.catalog import WS_EXPORT_TIMEOUT
from papers2zim.sources.wikisource.pipeline import WikisourcePipeline


def _work() -> Work:
    return Work(
        id="en_first-book-12345678",
        source="wikisource",
        title="First Book",
        formats=[
            Format(
                name="epub",
                media_type="application/epub+zip",
                url="https://ws-export.wmcloud.org/?lang=en&format=epub&page=First_Book",
            )
        ],
    )


def _pipeline(
    work: Work,
    engine: DownloadEngine | MagicMock,
    assembler: MagicMock,
    *,
    formats: list[str] | None = None,
):
    metadata = MagicMock()
    metadata.fetch.return_value = [work]
    return WikisourcePipeline(
        metadata=metadata,
        store=WorkStore(),
        assembler=assembler,
        progress=ScraperProgress(None),
        concurrency=1,
        formats=formats or ["epub", "pdf", "html"],
        zim_name="test",
        source_slug="wikisource",
        display_name="Wikisource",
        title_search=False,
        engine=engine,
    )


def _valid_epub() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_STORED) as archive:
        archive.writestr("mimetype", "application/epub+zip")
    return output.getvalue()


def _work_with_html() -> Work:
    work = _work()
    work.formats.append(
        Format(
            name="html",
            media_type="text/html",
            url="https://ws-export.wmcloud.org/?lang=en&format=htmlz&page=First_Book",
        )
    )
    return work


def _valid_html_archive() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_STORED) as archive:
        archive.writestr(
            "index.html",
            '<html><head><link href="style.css"/></head><body>'
            '<img src="images/pic.png"/></body></html>',
        )
        archive.writestr("style.css", "body {}")
        archive.writestr("images/pic.png", b"\x89PNG\r\n\x1a\npng bytes")
    return output.getvalue()


def test_enrich_descriptions_looks_them_up_on_wikidata():
    work = _work()
    engine = MagicMock()
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)
    pipeline.store.add(work)

    with patch(
        "papers2zim.sources.wikisource.pipeline.enrich_work_descriptions"
    ) as enrich:
        pipeline.enrich_descriptions()

    enrich.assert_called_once_with(pipeline.store, engine)


def test_process_ref_downloads_epub_and_marks_the_rest_unsupported():
    work = _work()
    engine = MagicMock()
    engine.fetch_bytes.return_value = _valid_epub()
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with (
        patch(
            "papers2zim.sources.wikisource.pipeline.extract_cover",
            return_value=None,
        ) as extract_cover_mock,
        patch.object(pipeline, "add_book_search_item") as add_search_item,
    ):
        pipeline.process_ref(WorkRef(id=work.id, source="wikisource"))

    extract_cover_mock.assert_called_once_with(
        _valid_epub(), "epub", declared_only=True
    )
    assert pipeline.store.get("wikisource", work.id) is work
    assert work.extra["unsupported_formats"] == ["pdf", "html"]
    assembler.add_item_for.assert_called_once_with(
        path=f"First Book.{work.id}.epub",
        content=_valid_epub(),
        mimetype="application/epub+zip",
        is_front=False,
    )
    add_search_item.assert_called_once_with(work, {"epub": _valid_epub()})


def test_process_ref_rejects_an_html_response_at_the_epub_url():
    work = _work()
    engine = MagicMock()
    engine.fetch_bytes.return_value = b"<!DOCTYPE html><html><body>nope</body></html>"
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with patch.object(pipeline, "add_book_search_item") as add_search_item:
        pipeline.process_ref(WorkRef(id=work.id, source="wikisource"))

    assert pipeline.store.get("wikisource", work.id) is None
    assembler.add_item_for.assert_not_called()
    add_search_item.assert_not_called()


def test_process_ref_attaches_a_cover_when_extractable():
    work = _work()
    engine = MagicMock()
    engine.fetch_bytes.return_value = _valid_epub()
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with patch(
        "papers2zim.sources.wikisource.pipeline.extract_cover",
        return_value=b"cover bytes",
    ) as extract_cover_mock:
        pipeline.process_ref(WorkRef(id=work.id, source="wikisource"))

    extract_cover_mock.assert_called_once_with(
        _valid_epub(), "epub", declared_only=True
    )
    assert work.extra["has_cover"] is True
    assert work.cover is not None
    assembler.add_item_for.assert_any_call(
        path=f"covers/{work.id}_cover_image.webp",
        content=b"cover bytes",
        mimetype="image/webp",
        is_front=False,
    )


def test_process_ref_adds_the_html_edition_pages():
    work = _work_with_html()
    engine = MagicMock()
    engine.fetch_bytes.side_effect = lambda url, **_: (
        _valid_epub() if "format=epub" in url else _valid_html_archive()
    )
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with (
        patch(
            "papers2zim.sources.wikisource.pipeline.extract_cover", return_value=None
        ),
        patch.object(pipeline, "add_book_search_item"),
    ):
        pipeline.process_ref(WorkRef(id=work.id, source="wikisource"))

    assert pipeline.store.get("wikisource", work.id) is work
    assert work.extra["unsupported_formats"] == ["pdf"]
    items = {
        call.kwargs["path"]: call.kwargs["mimetype"]
        for call in assembler.add_item_for.call_args_list
    }
    assert items == {
        f"First Book.{work.id}.epub": "application/epub+zip",
        f"First Book.{work.id}": "text/html",
        f"html/{work.id}/style.css": "text/css",
        f"html/{work.id}/images/pic.png": "image/png",
    }


@pytest.mark.parametrize("format_name", ["epub", "html"])
def test_process_ref_waits_for_ws_export_to_build_each_edition(format_name):
    work = _work_with_html()
    content = _valid_epub() if format_name == "epub" else _valid_html_archive()
    session = MagicMock()

    def export(_url, *, timeout, **_):
        if timeout <= DEFAULT_HTTP_TIMEOUT:
            raise requests.ReadTimeout("export takes longer than ten seconds")
        response = MagicMock()
        response.__enter__.return_value = response
        response.iter_content.return_value = [content]
        return response

    session.get.side_effect = export
    engine = DownloadEngine(session=session, max_retry_time=0)
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler, formats=[format_name])

    with (
        patch(
            "papers2zim.sources.wikisource.pipeline.extract_cover", return_value=None
        ),
        patch.object(pipeline, "add_book_search_item") as index,
    ):
        pipeline.process_ref(WorkRef(id=work.id, source="wikisource"))

    session.get.assert_called_once()
    assert session.get.call_args.kwargs["timeout"] == WS_EXPORT_TIMEOUT
    assert pipeline.store.get("wikisource", work.id) is work
    assert work.extra["unsupported_formats"] == []
    assert assembler.add_item_for.called
    assert set(index.call_args.args[1]) == {format_name}


@pytest.mark.parametrize("format_name", ["epub", "html"])
@pytest.mark.parametrize("status_code", [404, 503])
def test_process_ref_does_not_store_failed_exports(format_name, status_code):
    work = _work_with_html()
    response = requests.Response()
    response.status_code = status_code
    session = MagicMock()
    session.get.side_effect = requests.HTTPError(response=response)
    engine = DownloadEngine(session=session, max_retry_time=0)
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler, formats=[format_name])

    with patch.object(pipeline, "add_book_search_item") as index:
        pipeline.process_ref(WorkRef(id=work.id, source="wikisource"))

    assert pipeline.store.get("wikisource", work.id) is None
    assert work.extra["unsupported_formats"] == [format_name]
    assembler.add_item_for.assert_not_called()
    index.assert_not_called()


def test_process_ref_marks_html_unsupported_when_the_archive_is_invalid():
    work = _work_with_html()
    engine = MagicMock()
    engine.fetch_bytes.side_effect = lambda url, **_: (
        _valid_epub() if "format=epub" in url else b"<html>not a zip</html>"
    )
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with patch(
        "papers2zim.sources.wikisource.pipeline.extract_cover", return_value=None
    ):
        pipeline.process_ref(WorkRef(id=work.id, source="wikisource"))

    assert pipeline.store.get("wikisource", work.id) is work
    assert work.extra["unsupported_formats"] == ["pdf", "html"]


def test_process_ref_stores_html_only_when_no_binary_format_is_requested():
    work = _work_with_html()
    engine = MagicMock()
    engine.fetch_bytes.return_value = _valid_html_archive()
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler, formats=["html"])

    with patch.object(pipeline, "add_book_search_item") as add_search_item:
        pipeline.process_ref(WorkRef(id=work.id, source="wikisource"))

    assert pipeline.store.get("wikisource", work.id) is work
    assert work.extra["unsupported_formats"] == []
    add_search_item.assert_called_once()
    contents = add_search_item.call_args.args[1]
    assert set(contents) == {"html"}
