"""Tests for One More Library format resolution."""

from papers2zim.core.models import Format, Work
from papers2zim.sources.onemorelibrary.resolver import (
    OnemorelibraryFormatResolver,
)


def _work(*formats: Format) -> Work:
    return Work(
        id="2833",
        source="onemorelibrary",
        title="On Beauty",
        formats=list(formats),
    )


def test_resolve_returns_the_matching_download_link():
    work = _work(
        Format(
            name="epub",
            media_type="application/epub+zip",
            url="https://onemorelibrary.com/download?fid=14599",
        ),
        Format(
            name="pdf",
            media_type="application/pdf",
            url="https://onemorelibrary.com/download?fid=14598",
        ),
    )
    resolver = OnemorelibraryFormatResolver()

    request = resolver.resolve(work, "pdf")

    assert request is not None
    assert request.url.endswith("fid=14598")
    assert request.format_name == "pdf"
    assert request.extra["media_type"] == "application/pdf"


def test_resolve_returns_none_for_an_unsupported_format():
    resolver = OnemorelibraryFormatResolver()

    assert resolver.resolve(_work(), "html") is None


def test_resolve_returns_none_when_the_format_is_missing():
    work = _work(
        Format(
            name="pdf",
            media_type="application/pdf",
            url="https://onemorelibrary.com/download?fid=14598",
        )
    )
    resolver = OnemorelibraryFormatResolver()

    assert resolver.resolve(work, "epub") is None
