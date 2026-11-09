"""Tests for Bibliothèque numérique romande format resolution."""

from papers2zim.core.models import Format, Work
from papers2zim.sources.bibliothequenumeriqueromande.catalog import (
    BNR_SOURCE,
    EPUB_MEDIA_TYPE,
)
from papers2zim.sources.bibliothequenumeriqueromande.resolver import (
    BibliothequeNumeriqueRomandeFormatResolver,
)

WORK_ID = "87a3391f-6bf8-1014-9269-99b4f1e6d0dc"
EPUB_URL = "https://ebooks-bnr.com/opds/fetch.php?data=907&type=epub&id=449"


def _work(*formats: Format) -> Work:
    return Work(
        id=WORK_ID,
        source=BNR_SOURCE,
        title="CONTES",
        formats=list(formats),
    )


def test_resolve_epub_uses_the_acquisition_link():
    work = _work(Format(name="epub", media_type=EPUB_MEDIA_TYPE, url=EPUB_URL))

    request = BibliothequeNumeriqueRomandeFormatResolver().resolve(work, "epub")

    assert request is not None
    assert request.url == EPUB_URL
    assert request.format_name == "epub"


def test_resolve_returns_none_for_an_unsupported_format():
    work = _work(Format(name="epub", media_type=EPUB_MEDIA_TYPE, url=EPUB_URL))

    assert BibliothequeNumeriqueRomandeFormatResolver().resolve(work, "pdf") is None


def test_resolve_returns_none_when_the_format_has_no_url():
    work = _work(Format(name="epub", media_type=EPUB_MEDIA_TYPE, url=None))

    assert BibliothequeNumeriqueRomandeFormatResolver().resolve(work, "epub") is None
