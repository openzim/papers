"""Tests for the shared OPDS format resolver."""

from papers2zim.core.models import Format, Work
from papers2zim.core.opds_source import OpdsFormatResolver

WORK_ID = "87a3391f-6bf8-1014-9269-99b4f1e6d0dc"
EPUB_URL = "https://example.org/fetch.php?type=epub"
PDF_URL = "https://example.org/fetch.php?type=pdf"


def _work(*formats: Format) -> Work:
    return Work(
        id=WORK_ID,
        source="opds",
        title="Exemple",
        formats=list(formats),
    )


def test_resolve_epub_uses_the_acquisition_link():
    work = _work(
        Format(name="epub", media_type="application/epub+zip", url=EPUB_URL),
        Format(name="pdf", media_type="application/pdf", url=PDF_URL),
    )

    request = OpdsFormatResolver().resolve(work, "epub")

    assert request is not None
    assert request.url == EPUB_URL
    assert request.format_name == "epub"


def test_resolve_pdf_uses_its_own_link():
    work = _work(
        Format(name="epub", media_type="application/epub+zip", url=EPUB_URL),
        Format(name="pdf", media_type="application/pdf", url=PDF_URL),
    )

    request = OpdsFormatResolver().resolve(work, "pdf")

    assert request is not None
    assert request.url == PDF_URL


def test_resolve_returns_none_for_an_unsupported_format():
    work = _work(Format(name="epub", media_type="application/epub+zip", url=EPUB_URL))

    assert OpdsFormatResolver().resolve(work, "html") is None


def test_resolve_returns_none_when_the_format_has_no_url():
    work = _work(Format(name="epub", media_type="application/epub+zip", url=None))

    assert OpdsFormatResolver().resolve(work, "epub") is None
