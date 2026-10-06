"""Tests for generic (format-level) cover extraction."""

import io
import zipfile

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


def test_epub_cover_rejects_non_image_meta_cover_and_falls_back():
    epub = io.BytesIO()
    with zipfile.ZipFile(epub, "w") as archive:
        archive.writestr(
            "META-INF/container.xml",
            """<container><rootfiles><rootfile full-path="OPS/package.opf"/>
            </rootfiles></container>""",
        )
        archive.writestr(
            "OPS/package.opf",
            """<package><metadata><meta name="cover" content="titlepage"/>
            </metadata><manifest>
            <item id="titlepage" href="title.xhtml" media-type="application/xhtml+xml"/>
            <item id="real-cover" href="real-cover.jpg" media-type="image/jpeg"/>
            </manifest></package>""",
        )
        archive.writestr("OPS/title.xhtml", b"<html>title</html>")
        archive.writestr("OPS/real-cover.jpg", b"real cover image")

    assert _epub_cover(epub.getvalue()) == b"real cover image"
