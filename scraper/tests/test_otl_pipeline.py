"""Tests for OTL per-work processing."""

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch
from zipfile import ZIP_STORED, ZipFile

import pytest

from papers2zim.core.fulltext import extract_index_text
from papers2zim.core.models import Format, Work
from papers2zim.core.ports import WorkRef
from papers2zim.core.progress import ScraperProgress
from papers2zim.core.work_store import WorkStore
from papers2zim.sources.opentextbooks.html_mirror import HtmlEdition
from papers2zim.sources.opentextbooks.pipeline import OpenTextbookLibraryPipeline


def _edition(directory: Path, pages: dict[str, bytes]) -> HtmlEdition:
    files = {}
    for index, (path, content) in enumerate(pages.items()):
        fpath = directory / str(index)
        fpath.write_bytes(content)
        files[path] = fpath
    return HtmlEdition(pages=files)


def _pipeline(
    work: Work,
    engine: MagicMock,
    assembler: MagicMock,
    *,
    requested_languages: list[str] | None = None,
    books: list[str] | None = None,
):
    metadata = MagicMock()
    metadata.fetch.return_value = [work]
    pipeline = OpenTextbookLibraryPipeline(
        metadata=metadata,
        store=WorkStore(),
        assembler=assembler,
        progress=ScraperProgress(None),
        concurrency=1,
        formats=["epub", "pdf", "html"],
        zim_name="test",
        source_slug="opentextbooks",
        display_name="Open Textbook Library",
        title_search=False,
        requested_languages=requested_languages,
        books=books,
        engine=engine,
    )
    # keep the assembler calls to the book files; search items are tested apart
    pipeline.add_book_search_item = MagicMock()
    return pipeline


def _valid_epub() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_STORED) as archive:
        archive.writestr("mimetype", "application/epub+zip")
    return output.getvalue()


def test_process_ref_skips_work_in_another_language():
    work = Work(
        id="10",
        source="opentextbooks",
        title="Calculus",
        languages=["en"],
        formats=[
            Format(
                name="PDF",
                media_type="application/pdf",
                url="https://example.org/calculus.pdf",
            )
        ],
    )
    engine = MagicMock()
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler, requested_languages=["fr"])

    pipeline.process_ref(WorkRef(id="10", source="opentextbooks"))

    assert pipeline.store.get("opentextbooks", "10") is None
    engine.fetch_bytes.assert_not_called()
    assembler.add_item_for.assert_not_called()


def test_process_ref_keeps_work_in_a_requested_language():
    work = Work(
        id="10",
        source="opentextbooks",
        title="Calcul",
        languages=["fr"],
        formats=[
            Format(
                name="PDF",
                media_type="application/pdf",
                url="https://example.org/calcul.pdf",
            )
        ],
    )
    engine = MagicMock()
    engine.content_type.return_value = "application/pdf"
    engine.fetch_bytes.return_value = b"%PDF-1.7 pdf bytes"
    pipeline = _pipeline(work, engine, MagicMock(), requested_languages=["fre", "eng"])

    pipeline.process_ref(WorkRef(id="10", source="opentextbooks"))

    assert pipeline.store.get("opentextbooks", "10") is work


def test_process_ref_treats_mul_as_no_language_filter():
    work = Work(
        id="10",
        source="opentextbooks",
        title="Calculo",
        languages=["es"],
        formats=[
            Format(
                name="PDF",
                media_type="application/pdf",
                url="https://example.org/calculo.pdf",
            )
        ],
    )
    engine = MagicMock()
    engine.content_type.return_value = "application/pdf"
    engine.fetch_bytes.return_value = b"%PDF-1.7 pdf bytes"
    pipeline = _pipeline(work, engine, MagicMock(), requested_languages=["mul"])

    pipeline.process_ref(WorkRef(id="10", source="opentextbooks"))

    assert pipeline.store.get("opentextbooks", "10") is work


def test_process_ref_ignores_language_filter_for_explicit_books():
    work = Work(
        id="10",
        source="opentextbooks",
        title="Calculus",
        languages=["en"],
        formats=[
            Format(
                name="PDF",
                media_type="application/pdf",
                url="https://example.org/calculus.pdf",
            )
        ],
    )
    engine = MagicMock()
    engine.content_type.return_value = "application/pdf"
    engine.fetch_bytes.return_value = b"%PDF-1.7 pdf bytes"
    pipeline = _pipeline(
        work, engine, MagicMock(), requested_languages=["fr"], books=["10"]
    )

    pipeline.process_ref(WorkRef(id="10", source="opentextbooks"))

    assert pipeline.store.get("opentextbooks", "10") is work


def test_process_ref_exports_direct_files_and_marks_unavailable_formats():
    work = Work(
        id="10",
        source="opentextbooks",
        title="Calculus",
        formats=[
            Format(
                name="PDF",
                media_type="application/pdf",
                url="https://example.org/calculus.pdf",
            )
        ],
    )
    engine = MagicMock()
    engine.content_type.return_value = "application/pdf"
    engine.fetch_bytes.return_value = b"%PDF-1.7 pdf bytes"
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    pipeline.process_ref(WorkRef(id="10", source="opentextbooks"))

    assert pipeline.store.get("opentextbooks", "10") is work
    assert work.extra["unsupported_formats"] == ["epub", "html"]
    assembler.add_item_for.assert_called_once_with(
        path="Calculus.10.pdf",
        content=b"%PDF-1.7 pdf bytes",
        mimetype="application/pdf",
        is_front=False,
    )


def test_run_exports_a_downloaded_otl_work_without_popularity_metrics():
    work = Work(
        id="10",
        source="opentextbooks",
        title="Calculus",
        formats=[
            Format(
                name="PDF",
                media_type="application/pdf",
                url="https://example.org/calculus.pdf",
            )
        ],
    )
    engine = MagicMock()
    engine.content_type.return_value = "application/pdf"
    engine.fetch_bytes.return_value = b"%PDF-1.7 pdf bytes"
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with (
        patch(
            "papers2zim.sources.opentextbooks.pipeline.extract_cover",
            return_value=b"cover bytes",
        ),
        patch("papers2zim.core.pipeline.export_search_items") as search_items,
        patch("papers2zim.core.pipeline.generate_json_files") as json_files,
        patch("papers2zim.core.pipeline.generate_noscript_pages") as nojs_pages,
    ):
        pipeline.run([WorkRef(id="10", source="opentextbooks")])

    assert work.flames is None
    assert work.extra["has_cover"] is True
    assert work.cover is not None
    assembler.add_item_for.assert_any_call(
        path="covers/10_cover_image.webp",
        content=b"cover bytes",
        mimetype="image/webp",
        is_front=False,
    )
    search_items.assert_called_once()
    json_files.assert_called_once()
    nojs_pages.assert_called_once()


def test_process_ref_rejects_an_html_landing_page_at_a_pdf_url():
    work = Work(
        id="10",
        source="opentextbooks",
        title="Calculus",
        formats=[
            Format(
                name="PDF",
                media_type="application/pdf",
                url="https://example.org/calculus.pdf",
            )
        ],
    )
    engine = MagicMock()
    html = b"<!doctype html><html><body>Textbook</body></html>"
    engine.fetch_bytes.return_value = html
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with patch(
        "papers2zim.sources.opentextbooks.pipeline.fetch_page_cover"
    ) as fetch_cover:
        pipeline.process_ref(WorkRef(id="10", source="opentextbooks"))

    assert pipeline.store.get("opentextbooks", "10") is None
    assert work.extra["unsupported_formats"] == ["epub", "pdf", "html"]
    assembler.add_item_for.assert_not_called()
    fetch_cover.assert_not_called()


def test_html_controls_only_receive_validated_binary_formats(tmp_path):
    work = Work(
        id="10",
        source="opentextbooks",
        title="Calculus",
        formats=[
            Format(
                name="PDF",
                media_type="application/pdf",
                url="https://example.org/calculus.pdf",
            ),
            Format(
                name="Online",
                media_type="text/html",
                url="https://example.org/calculus/",
            ),
        ],
    )
    engine = MagicMock()
    engine.fetch_bytes.return_value = b"<!doctype html><html></html>"
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)
    edition = _edition(tmp_path, {"Calculus.10": b"<!doctype html><html></html>"})

    with patch(
        "papers2zim.sources.opentextbooks.pipeline.download_html_edition",
        return_value=edition,
    ) as mirror:
        pipeline.process_ref(WorkRef(id="10", source="opentextbooks"))

    assert mirror.call_args.args == (
        engine,
        work,
        "https://example.org/calculus/",
        ["html"],
    )
    assert work.extra["unsupported_formats"] == ["epub", "pdf"]
    assert b"html-reader-btn-pdf" not in edition.pages["Calculus.10"].read_bytes()


def test_html_is_not_mirrored_when_a_binary_format_is_available_after_it(tmp_path):
    work = Work(
        id="10",
        source="opentextbooks",
        title="Calculus",
        formats=[
            Format(
                name="PDF",
                media_type="application/pdf",
                url="https://example.org/calculus.pdf",
            ),
            Format(
                name="Online",
                media_type="text/html",
                url="https://example.org/calculus/",
            ),
        ],
    )
    engine = MagicMock()
    engine.fetch_bytes.return_value = b"%PDF-1.7 pdf bytes"
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)
    pipeline.formats = ["html", "pdf"]
    edition = _edition(tmp_path, {"Calculus.10": b"<!doctype html><html></html>"})

    with patch(
        "papers2zim.sources.opentextbooks.pipeline.download_html_edition",
        return_value=edition,
    ) as mirror:
        pipeline.process_ref(WorkRef(id="10", source="opentextbooks"))

    mirror.assert_not_called()
    assert work.extra["unsupported_formats"] == ["html"]
    assembler.add_item_for.assert_called_once_with(
        path="Calculus.10.pdf",
        content=b"%PDF-1.7 pdf bytes",
        mimetype="application/pdf",
        is_front=False,
    )


def test_process_ref_accepts_a_valid_epub_archive():
    work = Work(
        id="10",
        source="opentextbooks",
        title="Calculus",
        formats=[
            Format(
                name="eBook",
                media_type="application/epub+zip",
                url="https://example.org/calculus.epub",
            )
        ],
    )
    engine = MagicMock()
    engine.fetch_bytes.return_value = _valid_epub()
    assembler = MagicMock()
    pipeline = _pipeline(work, engine, assembler)

    with patch(
        "papers2zim.sources.opentextbooks.pipeline.optimize_epub_bytes",
        return_value=b"optimized epub",
    ) as optimize_epub:
        pipeline.process_ref(WorkRef(id="10", source="opentextbooks"))

    assert pipeline.store.get("opentextbooks", "10") is work
    assert "epub" not in work.extra["unsupported_formats"]
    optimize_epub.assert_called_once_with(_valid_epub(), log_context="OTL textbook 10")
    assembler.add_item_for.assert_called_once_with(
        path="Calculus.10.epub",
        content=b"optimized epub",
        mimetype="application/epub+zip",
        is_front=False,
    )


def test_process_ref_indexes_the_downloaded_binary_formats():
    work = Work(
        id="10",
        source="opentextbooks",
        title="Calculus",
        formats=[
            Format(
                name="PDF",
                media_type="application/pdf",
                url="https://example.org/calculus.pdf",
            )
        ],
    )
    engine = MagicMock()
    engine.fetch_bytes.return_value = b"%PDF-1.7 pdf bytes"
    pipeline = _pipeline(work, engine, MagicMock())

    with patch.object(pipeline, "add_book_search_item") as add_search_item:
        pipeline.process_ref(WorkRef(id="10", source="opentextbooks"))

    add_search_item.assert_called_once_with(work, {"pdf": b"%PDF-1.7 pdf bytes"})


def test_process_ref_indexes_the_html_pages_of_a_mirrored_edition(tmp_path):
    work = Work(
        id="10",
        source="opentextbooks",
        title="Calculus",
        formats=[
            Format(
                name="Online",
                media_type="text/html",
                url="https://example.org/calculus/",
            )
        ],
    )
    pipeline = _pipeline(work, MagicMock(), MagicMock())
    page = b"<!doctype html><html><body>Limits</body></html>"
    edition = _edition(tmp_path, {"Calculus.10": page, "style.css": b"p {}"})

    with (
        patch(
            "papers2zim.sources.opentextbooks.pipeline.download_html_edition",
            return_value=edition,
        ),
        patch.object(pipeline, "add_book_search_item") as add_search_item,
    ):
        pipeline.process_ref(WorkRef(id="10", source="opentextbooks"))

    contents = add_search_item.call_args.args[1]
    assert list(contents) == ["html"]
    assert [b"Limits" in p for p in contents["html"]] == [True]


def test_process_ref_does_not_index_a_work_without_any_download():
    work = Work(id="10", source="opentextbooks", title="Calculus")
    pipeline = _pipeline(work, MagicMock(), MagicMock())

    with patch.object(pipeline, "add_book_search_item") as add_search_item:
        pipeline.process_ref(WorkRef(id="10", source="opentextbooks"))

    add_search_item.assert_not_called()


def test_process_ref_stores_mirrored_assets_under_their_own_mimetype(tmp_path):
    work = Work(
        id="10",
        source="opentextbooks",
        title="Calculus",
        formats=[
            Format(
                name="Online",
                media_type="text/html",
                url="https://example.org/calculus/",
            )
        ],
    )
    assembler = MagicMock()
    pipeline = _pipeline(work, MagicMock(), assembler)
    page = b"<!doctype html><html><body>Limits</body></html>"
    edition = _edition(
        tmp_path,
        {
            "Calculus.10": page,
            "html/10/assets/a.css": b"p {}",
            "html/10/assets/b.js": b"var x;",
            "html/10/assets/c.png.webp": b"RIFF",
        },
    )

    with patch(
        "papers2zim.sources.opentextbooks.pipeline.download_html_edition",
        return_value=edition,
    ):
        pipeline.process_ref(WorkRef(id="10", source="opentextbooks"))

    mimetypes = {
        call.kwargs["path"]: call.kwargs["mimetype"]
        for call in assembler.add_item_for.call_args_list
    }
    assert mimetypes == {
        "Calculus.10": "text/html",
        "html/10/assets/a.css": "text/css",
        "html/10/assets/b.js": "text/javascript",
        "html/10/assets/c.png.webp": "image/webp",
    }


@pytest.mark.parametrize(
    "outcome", ["complete", "rejected", "download", "export", "index"]
)
def test_temporary_edition_storage_lives_through_indexing_and_is_cleaned(outcome):
    work = Work(
        id="10",
        source="opentextbooks",
        title="Calculus",
        formats=[
            Format(
                name="Online",
                media_type="text/html",
                url="https://example.org/calculus/",
            )
        ],
    )
    assembler = MagicMock()
    pipeline = _pipeline(work, MagicMock(), assembler)
    directories = []

    def mirror(_engine, _work, _url, _formats, *, directory):
        directories.append(directory)
        edition = _edition(
            directory,
            {
                "Calculus.10": b"<html><body>First chapter</body></html>",
                "html/10/last.html": b"<html><body>Last chapter</body></html>",
                "html/10/assets/style.css": b"p {}",
            },
        )
        if outcome == "download":
            raise OSError("download failed")
        return None if outcome == "rejected" else edition

    def index(_work, contents):
        assert directories[0].is_dir()
        assert not isinstance(contents["html"], list)
        text = extract_index_text("html", contents["html"])
        assert "First chapter" in text
        assert "Last chapter" in text
        assert "p {}" not in text
        if outcome == "index":
            raise OSError("index failed")

    index_mock = MagicMock(side_effect=index)
    pipeline.add_book_search_item = index_mock
    if outcome == "export":
        assembler.add_item_for.side_effect = OSError("export failed")
    with patch(
        "papers2zim.sources.opentextbooks.pipeline.download_html_edition",
        side_effect=mirror,
    ):
        if outcome in {"download", "export", "index"}:
            with pytest.raises(OSError, match=f"{outcome} failed"):
                pipeline.process_ref(WorkRef(id="10", source="opentextbooks"))
        else:
            pipeline.process_ref(WorkRef(id="10", source="opentextbooks"))

    assert len(directories) == 1
    assert not directories[0].exists()
    if outcome == "complete":
        index_mock.assert_called_once()
        assert len(assembler.add_item_for.call_args_list) == 3
        assert all(
            isinstance(call.kwargs["content"], bytes)
            for call in assembler.add_item_for.call_args_list
        )
    elif outcome == "rejected":
        assembler.add_item_for.assert_not_called()
