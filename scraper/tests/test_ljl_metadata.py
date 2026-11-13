"""Tests for Littérature jeunesse libre feed metadata mapping."""

from papers2zim.core.models import Format
from papers2zim.core.ports import WorkRef
from papers2zim.core.utils import slug_id
from papers2zim.sources.litteraturejeunesselibre.catalog import (
    EPUB_MEDIA_TYPE,
    LJL_SOURCE,
    PDF_MEDIA_TYPE,
)
from papers2zim.sources.litteraturejeunesselibre.metadata import (
    DEFAULT_LANGUAGE,
    LitteratureJeunesseLibreMetadata,
)

WORK_ID = "87a3391f-6bf8-1014-9269-99b4f1e6d0dc"
EPUB_URL = "https://litterature-jeunesse-libre.fr/bbs/opds/fetch.php?data=907&type=epub"
PDF_URL = "https://litterature-jeunesse-libre.fr/bbs/opds/fetch.php?data=907&type=pdf"
COVER_URL = "https://litterature-jeunesse-libre.fr/bbs/opds/fetch.php?height=164"
DESCRIPTION = "Un album pour découvrir les animaux de la ferme."


def _ref(**overrides) -> WorkRef:
    extra = {
        "title": "Animaux",
        "formats": [
            Format(name="epub", media_type=EPUB_MEDIA_TYPE, url=EPUB_URL),
            Format(name="pdf", media_type=PDF_MEDIA_TYPE, url=PDF_URL),
        ],
        "categories": ["Animaux"],
        "languages": ["fr"],
        "authors": ["Jeanne Auteur", "Pierre Illustrateur"],
        "cover_url": COVER_URL,
        "description": DESCRIPTION,
    }
    extra.update(overrides)
    return WorkRef(id=WORK_ID, source=LJL_SOURCE, extra=extra)


def test_fetch_maps_the_feed_fields_to_a_work():
    (work,) = LitteratureJeunesseLibreMetadata().fetch([_ref()])

    assert work.id == WORK_ID
    assert work.source == LJL_SOURCE
    assert work.title == "Animaux"
    assert work.languages == ["fr"]
    assert work.description == DESCRIPTION
    assert work.source_url == EPUB_URL
    book_format = work.formats[0]
    assert book_format.name == "epub"
    assert book_format.media_type == EPUB_MEDIA_TYPE
    assert book_format.url == EPUB_URL
    assert work.cover is not None
    assert work.cover.source_url == COVER_URL
    assert [(creator.display_name, creator.sort_name) for creator in work.creators] == [
        ("Jeanne Auteur", "Jeanne Auteur"),
        ("Pierre Illustrateur", "Pierre Illustrateur"),
    ]
    collections = [
        (collection.id, collection.name, collection.kind)
        for collection in work.collections
    ]
    assert collections == [
        (slug_id("Animaux"), "Animaux", "category"),
    ]


def test_fetch_keeps_every_download_format():
    (work,) = LitteratureJeunesseLibreMetadata().fetch([_ref()])

    assert [(fmt.name, fmt.media_type, fmt.url) for fmt in work.formats] == [
        ("epub", EPUB_MEDIA_TYPE, EPUB_URL),
        ("pdf", PDF_MEDIA_TYPE, PDF_URL),
    ]


def test_fetch_accepts_serialized_formats():
    (work,) = LitteratureJeunesseLibreMetadata().fetch(
        [
            _ref(
                formats=[
                    {
                        "name": "epub",
                        "media_type": EPUB_MEDIA_TYPE,
                        "url": EPUB_URL,
                        "local_path": None,
                        "size": None,
                    }
                ]
            )
        ]
    )

    assert work.formats == [
        Format(
            name="epub",
            media_type=EPUB_MEDIA_TYPE,
            url=EPUB_URL,
            local_path=None,
            size=None,
        )
    ]


def test_fetch_normalizes_iso_639_3_language_codes():
    (work,) = LitteratureJeunesseLibreMetadata().fetch(
        [_ref(languages=["fra", "eng", "fra"])]
    )

    assert work.languages == ["fr", "en"]


def test_fetch_tolerates_missing_author_cover_and_language():
    (work,) = LitteratureJeunesseLibreMetadata().fetch(
        [_ref(authors=[], cover_url=None, languages=[], categories=[])]
    )

    assert work.creators == []
    assert work.cover is None
    assert work.languages == [DEFAULT_LANGUAGE]
    assert work.collections == []


def test_fetch_tolerates_missing_download_links():
    (work,) = LitteratureJeunesseLibreMetadata().fetch([_ref(formats=[])])

    assert work.formats == []
    assert work.source_url is None
