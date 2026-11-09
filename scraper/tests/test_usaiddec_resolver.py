"""Tests for USAID DEC Archive format resolution."""

from papers2zim.core.models import Format, Work
from papers2zim.sources.usaiddec.resolver import UsaidDecFormatResolver


def _work(*formats: Format) -> Work:
    return Work(
        id="PA00JMRT",
        source="usaiddec",
        title="Evaluation report",
        formats=list(formats),
    )


def test_resolve_pdf_returns_the_catalog_url():
    work = _work(
        Format(name="pdf", media_type="application/pdf", url="https://a.org/r.pdf")
    )

    request = UsaidDecFormatResolver().resolve(work, "pdf")

    assert request is not None
    assert request.url == "https://a.org/r.pdf"
    assert request.format_name == "pdf"
    assert request.extra["media_type"] == "application/pdf"


def test_resolve_rejects_formats_the_source_does_not_offer():
    work = _work(
        Format(name="pdf", media_type="application/pdf", url="https://a.org/r.pdf")
    )

    assert UsaidDecFormatResolver().resolve(work, "epub") is None


def test_resolve_without_any_pdf_returns_nothing():
    work = _work(Format(name="pdf", media_type="application/pdf"))

    assert UsaidDecFormatResolver().resolve(work, "pdf") is None
