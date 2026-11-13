"""Tests for Littérature jeunesse libre format resolution."""

from papers2zim.core.models import Format, Work
from papers2zim.sources.litteraturejeunesselibre.catalog import (
    EPUB_MEDIA_TYPE,
    LJL_SOURCE,
    PDF_MEDIA_TYPE,
)
from papers2zim.sources.litteraturejeunesselibre.resolver import (
    LitteratureJeunesseLibreFormatResolver,
)

WORK_ID = "87a3391f-6bf8-1014-9269-99b4f1e6d0dc"
EPUB_URL = "https://litterature-jeunesse-libre.fr/bbs/opds/fetch.php?data=907&type=epub"
PDF_URL = "https://litterature-jeunesse-libre.fr/bbs/opds/fetch.php?data=907&type=pdf"


def _work(*formats: Format) -> Work:
    return Work(
        id=WORK_ID,
        source=LJL_SOURCE,
        title="Animaux",
        formats=list(formats),
    )


def test_resolve_epub_uses_the_acquisition_link():
    work = _work(
        Format(name="epub", media_type=EPUB_MEDIA_TYPE, url=EPUB_URL),
        Format(name="pdf", media_type=PDF_MEDIA_TYPE, url=PDF_URL),
    )

    request = LitteratureJeunesseLibreFormatResolver().resolve(work, "epub")

    assert request is not None
    assert request.url == EPUB_URL
    assert request.format_name == "epub"


def test_resolve_pdf_uses_its_own_link():
    work = _work(
        Format(name="epub", media_type=EPUB_MEDIA_TYPE, url=EPUB_URL),
        Format(name="pdf", media_type=PDF_MEDIA_TYPE, url=PDF_URL),
    )

    request = LitteratureJeunesseLibreFormatResolver().resolve(work, "pdf")

    assert request is not None
    assert request.url == PDF_URL


def test_resolve_returns_none_for_an_unsupported_format():
    work = _work(Format(name="epub", media_type=EPUB_MEDIA_TYPE, url=EPUB_URL))

    assert LitteratureJeunesseLibreFormatResolver().resolve(work, "html") is None


def test_resolve_returns_none_when_the_format_has_no_url():
    work = _work(Format(name="epub", media_type=EPUB_MEDIA_TYPE, url=None))

    assert LitteratureJeunesseLibreFormatResolver().resolve(work, "epub") is None
