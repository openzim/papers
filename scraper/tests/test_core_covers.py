"""Tests for generic (format-level) cover extraction."""

import io
import zipfile

from PIL import Image

from papers2zim.core.covers import _epub_cover, extract_cover


def test_extract_cover_returns_none_for_unsupported_format():
    assert extract_cover(b"whatever", "txt") is None


def test_epub_cover_decodes_manifest_href_before_archive_lookup():
    epub = io.BytesIO()
    with zipfile.ZipFile(epub, "w") as archive:
        archive.writestr(
            "META-INF/container.xml",
            """<container><rootfiles><rootfile full-path="OPS/package.opf"/>
            </rootfiles></container>""",
        )
        archive.writestr(
            "OPS/package.opf",
            """<package><metadata><meta name="cover" content="cover"/>
            </metadata><manifest><item id="cover" href="cover%20image.jpg"
            media-type="image/jpeg"/></manifest></package>""",
        )
        archive.writestr("OPS/cover image.jpg", b"cover image")

    assert _epub_cover(epub.getvalue()) == b"cover image"


def test_extract_cover_scales_result_down_to_max_width(make_epub):
    cover = extract_cover(make_epub(size=(640, 960)), "epub", max_width=400)
    assert cover is not None
    assert Image.open(io.BytesIO(cover)).size == (400, 600)


def test_extract_cover_never_upscales_to_reach_max_width(make_epub):
    cover = extract_cover(make_epub(size=(64, 96)), "epub", max_width=400)
    assert cover is not None
    assert Image.open(io.BytesIO(cover)).size == (64, 96)


def test_extract_cover_keeps_declared_cover_when_not_restricted(make_epub):
    assert extract_cover(make_epub(), "epub") is not None


def test_extract_cover_declared_only_ignores_undeclared_image(make_epub):
    assert extract_cover(make_epub(declared=False), "epub", declared_only=True) is None


def test_extract_cover_falls_back_to_undeclared_image_by_default(make_epub):
    assert extract_cover(make_epub(declared=False), "epub") is not None
