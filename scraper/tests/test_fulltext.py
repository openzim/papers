"""Tests for core.fulltext: picking the format to index and extracting its text."""

from io import BytesIO
from unittest.mock import patch
from zipfile import ZIP_STORED, ZipFile

import pymupdf
import pytest

from papers2zim.core import fulltext
from papers2zim.core.fulltext import extract_index_text, index_format_candidates


def make_epub(text: str) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w") as epub:
        epub.writestr("mimetype", "application/epub+zip", ZIP_STORED)
        epub.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0"?>'
            '<container version="1.0" '
            'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfiles><rootfile full-path="content.opf" '
            'media-type="application/oebps-package+xml"/></rootfiles></container>',
        )
        epub.writestr(
            "content.opf",
            '<?xml version="1.0" encoding="utf-8"?>'
            '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
            'unique-identifier="id">'
            '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
            '<dc:identifier id="id">test-book</dc:identifier>'
            "<dc:title>Test Book</dc:title><dc:language>en</dc:language>"
            "</metadata><manifest>"
            '<item id="c1" href="c1.xhtml" media-type="application/xhtml+xml"/>'
            '</manifest><spine><itemref idref="c1"/></spine></package>',
        )
        epub.writestr(
            "c1.xhtml",
            '<?xml version="1.0" encoding="utf-8"?>'
            '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>One</title>'
            f"</head><body><p>{text}</p></body></html>",
        )
    return output.getvalue()


def make_pdf(text: str) -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), text)
    return doc.tobytes()


@pytest.mark.parametrize(
    "available, forced, expected",
    [
        (["epub", "pdf", "html"], None, ["html", "epub", "pdf"]),
        (["pdf", "epub"], None, ["epub", "pdf"]),
        (["pdf"], None, ["pdf"]),
        ([], None, []),
        (["mobi"], None, []),
        (["html", "pdf"], "pdf", ["pdf", "html"]),
        # a forced format the book lacks falls back to the preference order
        (["html", "epub"], "pdf", ["html", "epub"]),
    ],
)
def test_index_format_candidates(
    available: list[str], forced: str | None, expected: list[str]
):
    assert index_format_candidates(available, forced) == expected


def test_extract_index_text_from_html_skips_markup_and_scripts():
    html = (
        "<html><head><title>T</title><style>p {color: red}</style></head>"
        "<body><p>Call me <b>Ishmael</b>.</p><script>var x = 1;</script></body></html>"
    )
    assert extract_index_text("html", html) == "Call me Ishmael."


def test_extract_index_text_from_html_keeps_words_whole_and_blocks_apart():
    html = '<p><span class="dropcap">I</span>t was cold.</p><p>Snow</p><p>fell.</p>'
    assert extract_index_text("html", html) == "It was cold. Snow fell."


def test_extract_index_text_from_several_html_pages():
    text = extract_index_text(
        "html", ["<p>first chapter text</p>", "<p>second chapter text</p>"]
    )
    assert "first chapter text" in text
    assert "second chapter text" in text


def test_extract_index_text_from_epub():
    text = extract_index_text("epub", make_epub("The keeper trimmed the wick."))
    assert "The keeper trimmed the wick." in text


@pytest.mark.parametrize(
    ("format_name", "helper"),
    [("epub", "get_epub_index_data"), ("pdf", "get_pdf_index_data")],
)
def test_extract_index_text_reads_each_format_with_its_own_helper(format_name, helper):
    with patch.object(fulltext, helper) as get_index_data:
        get_index_data.return_value.get_content.return_value = "book text"
        assert extract_index_text(format_name, b"book bytes") == "book text"
    get_index_data.assert_called_once_with(content=b"book bytes")


def test_extract_index_text_from_pdf():
    text = extract_index_text("pdf", make_pdf("Gulls circled the breakwater."))
    assert "Gulls circled the breakwater." in text


def test_extract_index_text_from_a_broken_file_is_empty():
    with patch.object(fulltext.logger, "warning") as warning:
        assert extract_index_text("pdf", b"not a pdf at all", "book 1") == ""
    warning.assert_called_once()
    assert "book 1" in warning.call_args.args


def test_extract_index_text_skips_the_injected_reader_controls():
    html = (
        '<body><div id="html-reader-controls"><a>Download EPUB</a></div>'
        "<p>Limits and continuity</p></body>"
    )
    assert extract_index_text("html", html) == "Limits and continuity"
