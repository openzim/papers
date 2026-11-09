"""Tests for Bibliothèque numérique romande feed metadata mapping."""

# ruff: noqa: RUF001

from papers2zim.core.ports import WorkRef
from papers2zim.core.utils import slug_id
from papers2zim.sources.bibliothequenumeriqueromande.catalog import (
    BNR_LANGUAGE,
    BNR_SOURCE,
    EPUB_MEDIA_TYPE,
)
from papers2zim.sources.bibliothequenumeriqueromande.metadata import (
    BibliothequeNumeriqueRomandeMetadata,
)

WORK_ID = "87a3391f-6bf8-1014-9269-99b4f1e6d0dc"
EPUB_URL = "https://ebooks-bnr.com/opds/fetch.php?data=907&type=epub&id=449"
COVER_URL = "https://ebooks-bnr.com/opds/fetch.php?height=164&id=449"
DESCRIPTION = (
    "Les contes de Perrault ont survécu depuis le 17e siècle et font, encore "
    "aujourd’hui, les délices des enfants comme des adultes."
)


def _ref(**overrides) -> WorkRef:
    extra = {
        "title": "CONTES",
        "source_url": EPUB_URL,
        "categories": ["17e", "Conte", "Littérature française"],
        "author": "Charles Perrault",
        "cover_url": COVER_URL,
        "description": DESCRIPTION,
    }
    extra.update(overrides)
    return WorkRef(id=WORK_ID, source=BNR_SOURCE, extra=extra)


def test_fetch_maps_the_feed_fields_to_a_work():
    (work,) = BibliothequeNumeriqueRomandeMetadata().fetch([_ref()])

    assert work.id == WORK_ID
    assert work.source == BNR_SOURCE
    assert work.title == "CONTES"
    assert work.languages == [BNR_LANGUAGE]
    assert work.description == DESCRIPTION
    assert work.source_url == EPUB_URL
    (creator,) = work.creators
    assert creator.display_name == "Charles Perrault"
    assert creator.sort_name == "Charles Perrault"
    assert creator.id.startswith("charles-perrault-")
    (book_format,) = work.formats
    assert book_format.name == "epub"
    assert book_format.media_type == EPUB_MEDIA_TYPE
    assert book_format.url == EPUB_URL
    assert work.cover is not None
    assert work.cover.source_url == COVER_URL
    collections = [
        (collection.id, collection.name, collection.kind)
        for collection in work.collections
    ]
    assert collections == [
        (slug_id("17e"), "17e", "category"),
        (slug_id("Conte"), "Conte", "category"),
        (slug_id("Littérature française"), "Littérature française", "category"),
    ]


def test_fetch_tolerates_missing_cover_categories_and_download_link():
    (work,) = BibliothequeNumeriqueRomandeMetadata().fetch(
        [_ref(cover_url=None, categories=[], source_url=None)]
    )

    assert work.cover is None
    assert work.collections == []
    assert work.formats == []
    assert work.source_url is None
    assert work.creators
    assert work.description == DESCRIPTION
