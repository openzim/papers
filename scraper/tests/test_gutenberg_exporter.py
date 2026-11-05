"""Tests for Gutenberg cover image handling in exporter.py."""

import io
from unittest.mock import ANY, MagicMock, patch

import pytest
from PIL import Image

from papers2zim.core.models import Work
from papers2zim.sources.gutenberg.exporter import (
    COVER_MAX_WIDTH,
    export_book,
    handle_book_files,
    is_cover_asset,
)


def _image_bytes(img_format: str) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), "white").save(buf, format=img_format)
    return buf.getvalue()


def _work(book_id="11", **extra) -> Work:
    return Work(
        id=book_id,
        source="gutenberg",
        title="Test Book",
        languages=["en"],
        extra={"has_cover": True, **extra},
    )


@pytest.mark.parametrize(
    ("book_id", "filename", "expected"),
    [
        ("11", "11/cover.jpg", True),
        ("11", "11/cover.jpeg", True),
        ("11", "11/cover.png", True),
        ("11", "11/cover.webp", True),
        ("11", "11/11-cover.png", True),
        ("11", "11/images/11-cover.png", True),
        ("11", "11/cover.xml", False),
        ("11", "11/colophon.png", False),
        ("11", "11/discover.jpg", False),
        ("84", "11/cover.jpg", False),
    ],
)
def test_is_cover_asset(book_id: str, filename: str, expected):
    assert is_cover_asset(book_id, filename) is expected


def test_handle_book_files_detects_bundled_cover_asset():
    work = _work()
    assembler = MagicMock()
    handle_book_files(
        work,
        {"11/cover.jpg": _image_bytes("JPEG")},
        formats=["html"],
        assembler=assembler,
    )
    assert work.extra["html_cover_path"] == "11/cover.jpg.webp"
    assembler.add_item_for.assert_called_once_with(
        path="11/cover.jpg.webp",
        content=ANY,
        is_front=False,
    )


def _stored_paths(assembler) -> list[str]:
    """ZIM paths the book files were stored under."""
    return [call.kwargs.get("path") for call in assembler.add_item_for.call_args_list]


def test_handle_book_files_keeps_book_when_epub_is_not_an_archive():
    """#135: unreadable EPUB bytes cost the format, never the whole book"""
    work = _work()
    assembler = MagicMock()
    book_files = {
        "11.html": b"<html><body><p>Book content</p></body></html>",
        "11.epub": b"<!doctype html><html><body>server error</body></html>",
    }
    handle_book_files(work, book_files, formats=["html", "epub"], assembler=assembler)

    assert "11.epub" not in book_files
    assert work.extra["unsupported_formats"] == ["epub"]
    # stored as an article, without the EPUB and without retrying it as an asset
    assert "Test Book.11.epub" not in _stored_paths(assembler)
    assert "Test Book.11" in _stored_paths(assembler)


def test_epub_is_stored_unoptimized_when_optimization_fails(make_epub):
    work = _work()
    assembler = MagicMock()
    epub = make_epub()
    with patch(
        "papers2zim.sources.gutenberg.exporter.optimize_epub_bytes",
        side_effect=RuntimeError("cannot rewrite the package"),
    ):
        handle_book_files(
            work, {"11.epub": epub}, formats=["epub"], assembler=assembler
        )

    assert work.extra.get("unsupported_formats", []) == []
    assert "Test Book.11.epub" in _stored_paths(assembler)


def test_handle_book_files_keeps_book_when_a_format_cannot_be_written(make_epub):
    work = _work()
    assembler = MagicMock()

    def store_or_fail(**kwargs):
        if kwargs["path"].endswith(".epub"):
            raise RuntimeError("ZIM is full")

    assembler.add_item_for.side_effect = store_or_fail
    book_files = {"11.epub": make_epub()}
    handle_book_files(work, book_files, formats=["epub"], assembler=assembler)

    assert book_files == {}
    assert work.extra["unsupported_formats"] == ["epub"]


def test_export_book_aliases_bundled_cover_and_skips_mirror_download():
    work = _work()
    assembler = MagicMock()
    engine = MagicMock()
    with patch("papers2zim.sources.gutenberg.exporter.download_book_cover") as download:
        export_book(
            work=work,
            book_files={"11/cover.jpg": _image_bytes("JPEG")},
            formats=["html"],
            mirror_url="https://example.com",
            assembler=assembler,
            engine=engine,
            _zim_name="test",
            _title_search=False,
        )
    download.assert_not_called()
    assembler.add_alias.assert_called_once_with(
        path="covers/11_cover_image.webp", title="", target="11/cover.jpg.webp"
    )


def test_export_book_downloads_cover_when_not_bundled():
    work = _work()
    assembler = MagicMock()
    engine = MagicMock()
    with patch(
        "papers2zim.sources.gutenberg.exporter.download_book_cover",
        return_value=_image_bytes("JPEG"),
    ) as download:
        export_book(
            work=work,
            book_files={"11/colophon.png": _image_bytes("PNG")},
            formats=["html"],
            mirror_url="https://example.com",
            assembler=assembler,
            engine=engine,
            _zim_name="test",
            _title_search=False,
        )
    download.assert_called_once()
    assembler.add_alias.assert_not_called()
    assembler.add_item_for.assert_any_call(
        path="covers/11_cover_image.webp",
        content=ANY,
        mimetype="image/webp",
        is_front=False,
    )


def test_optimize_failure_leaves_cover_undetected_and_triggers_mirror_download():
    work = _work()
    assembler = MagicMock()
    engine = MagicMock()
    with patch(
        "papers2zim.sources.gutenberg.exporter.optimize_content",
        side_effect=Exception("cannot optimize cover"),
    ):
        handle_book_files(
            work,
            {"11/cover.jpg": b"corrupt-image-bytes"},
            formats=["html"],
            assembler=assembler,
        )
    assert "html_cover_path" not in work.extra
    with patch(
        "papers2zim.sources.gutenberg.exporter.download_book_cover",
        return_value=_image_bytes("JPEG"),
    ) as download:
        export_book(
            work=work,
            book_files={"11/cover.jpg": b"corrupt-image-bytes"},
            formats=["html"],
            mirror_url="https://example.com",
            assembler=assembler,
            engine=engine,
            _zim_name="test",
            _title_search=False,
        )
    download.assert_called_once()
    assembler.add_alias.assert_not_called()
    assembler.add_item_for.assert_any_call(
        path="covers/11_cover_image.webp",
        content=ANY,
        mimetype="image/webp",
        is_front=False,
    )


def test_export_book_still_uses_icon_linked_html_cover():
    html = (
        b'<html><head><link rel="icon" href="images/icon.jpg"/></head>'
        b"<body><p>Book content</p></body></html>"
    )
    work = _work()
    assembler = MagicMock()
    engine = MagicMock()
    with patch("papers2zim.sources.gutenberg.exporter.download_book_cover") as download:
        export_book(
            work=work,
            book_files={
                "11.html": html,
                "11/images/icon.jpg": _image_bytes("JPEG"),
            },
            formats=["html"],
            mirror_url="https://example.com",
            assembler=assembler,
            engine=engine,
            _zim_name="test",
            _title_search=False,
        )
    download.assert_not_called()
    assembler.add_alias.assert_called_once_with(
        path="covers/11_cover_image.webp", title="", target="11/images/icon.jpg.webp"
    )


def _stored_cover(assembler):
    """Return the bytes stored for the ZIM cover path."""
    path = "covers/11_cover_image.webp"
    for call in assembler.add_item_for.call_args_list:
        if call.kwargs.get("path") == path:
            return call.kwargs["content"]
    return None


def test_export_book_prefers_embedded_epub_cover_over_mirror(make_epub):
    work = _work()
    assembler = MagicMock()
    engine = MagicMock()
    with patch("papers2zim.sources.gutenberg.exporter.download_book_cover") as download:
        export_book(
            work=work,
            book_files={"11.epub": make_epub(size=(800, 1200))},
            formats=["epub"],
            mirror_url="https://example.com",
            assembler=assembler,
            engine=engine,
            _zim_name="test",
            _title_search=False,
        )
    download.assert_not_called()
    cover = _stored_cover(assembler)
    assert cover is not None
    assert Image.open(io.BytesIO(cover)).size == (COVER_MAX_WIDTH, 600)


def test_export_book_falls_back_to_mirror_when_epub_cover_is_undeclared(make_epub):
    work = _work()
    assembler = MagicMock()
    engine = MagicMock()
    with patch(
        "papers2zim.sources.gutenberg.exporter.download_book_cover",
        return_value=_image_bytes("JPEG"),
    ) as download:
        export_book(
            work=work,
            book_files={"11.epub": make_epub(declared=False)},
            formats=["epub"],
            mirror_url="https://example.com",
            assembler=assembler,
            engine=engine,
            _zim_name="test",
            _title_search=False,
        )
    download.assert_called_once()
    assert _stored_cover(assembler) is not None


def test_export_book_falls_back_to_mirror_when_no_epub_is_present():
    work = _work()
    assembler = MagicMock()
    engine = MagicMock()
    with patch(
        "papers2zim.sources.gutenberg.exporter.download_book_cover",
        return_value=_image_bytes("JPEG"),
    ) as download:
        export_book(
            work=work,
            book_files={"11.pdf": b"%PDF-1.4 fake"},
            formats=["pdf"],
            mirror_url="https://example.com",
            assembler=assembler,
            engine=engine,
            _zim_name="test",
            _title_search=False,
        )
    download.assert_called_once()
    assert _stored_cover(assembler) is not None


def test_export_book_prefers_bundled_cover_over_mismatched_icon_link():
    """Regression test for #49: PG sometimes tags a decorative illustration as
    the `<link rel="icon">` cover (e.g. a thin title-page divider) while also
    bundling the real cover under the standard cover.*/{id}-cover.* naming.
    The bundled asset must win, even though the icon-linked file is processed
    first (as in the actual zip order for the reported book)."""
    html = (
        b'<html><head><link rel="icon" href="images/illu_title.png"/></head>'
        b"<body><p>Book content</p></body></html>"
    )
    work = _work()
    assembler = MagicMock()
    engine = MagicMock()
    with patch("papers2zim.sources.gutenberg.exporter.download_book_cover") as download:
        export_book(
            work=work,
            book_files={
                "11.html": html,
                "11/images/illu_title.png": _image_bytes("PNG"),
                "11/cover.jpg": _image_bytes("JPEG"),
            },
            formats=["html"],
            mirror_url="https://example.com",
            assembler=assembler,
            engine=engine,
            _zim_name="test",
            _title_search=False,
        )
    download.assert_not_called()
    assembler.add_alias.assert_called_once_with(
        path="covers/11_cover_image.webp", title="", target="11/cover.jpg.webp"
    )


def test_handle_book_files_leaves_main_html_indexing_to_the_book_entry():
    # the book text is indexed on the book's search entry instead (#43)
    work = _work()
    assembler = MagicMock()
    with patch(
        "papers2zim.sources.gutenberg.exporter.update_html_for_static",
        return_value="<p>rewritten</p>",
    ):
        handle_book_files(
            work, {"11.html": b"<p>text</p>"}, formats=["html"], assembler=assembler
        )
    main_html = assembler.add_item_for.call_args.kwargs
    assert main_html["path"] == "Test Book.11"
    assert main_html["mimetype"] == "text/html"
    assert main_html.get("auto_index", False) is False
