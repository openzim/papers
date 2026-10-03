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
        ("11", "11_cover.jpg", True),
        ("11", "11_cover.jpeg", True),
        ("11", "11_cover.png", True),
        ("11", "11_cover.webp", True),
        ("11", "11_11-cover.png", True),
        ("11", "11_cover.xml", False),
        ("11", "11_colophon.png", False),
        ("11", "11_discover.jpg", False),
        ("84", "11_cover.jpg", False),
    ],
)
def test_is_cover_asset(book_id: str, filename: str, expected):
    assert is_cover_asset(book_id, filename) is expected


def test_handle_book_files_detects_bundled_cover_asset():
    work = _work()
    assembler = MagicMock()
    handle_book_files(
        work,
        {"11_cover.jpg": _image_bytes("JPEG")},
        formats=["html"],
        assembler=assembler,
    )
    assert work.extra["html_cover_path"] == "11_cover.webp"
    assembler.add_item_for.assert_called_once_with(
        path="11_cover.webp",
        content=ANY,
        is_front=False,
    )


def test_export_book_aliases_bundled_cover_and_skips_mirror_download():
    work = _work()
    assembler = MagicMock()
    engine = MagicMock()
    with patch("papers2zim.sources.gutenberg.exporter.download_book_cover") as download:
        export_book(
            work=work,
            book_files={"11_cover.jpg": _image_bytes("JPEG")},
            formats=["html"],
            mirror_url="https://example.com",
            assembler=assembler,
            engine=engine,
            _zim_name="test",
            _title_search=False,
        )
    download.assert_not_called()
    assembler.add_alias.assert_called_once_with(
        path="covers/11_cover_image.webp", title="", target="11_cover.webp"
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
            book_files={"11_colophon.png": _image_bytes("PNG")},
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
            {"11_cover.jpg": b"corrupt-image-bytes"},
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
            book_files={"11_cover.jpg": b"corrupt-image-bytes"},
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
                "11_icon.jpg": _image_bytes("JPEG"),
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
        path="covers/11_cover_image.webp", title="", target="11_icon.webp"
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
                "11_illu_title.png": _image_bytes("PNG"),
                "11_cover.jpg": _image_bytes("JPEG"),
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
        path="covers/11_cover_image.webp", title="", target="11_cover.webp"
    )
