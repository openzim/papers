"""Tests for Bibliothèque numérique romande catalog discovery."""

# ruff: noqa: RUF001

import pytest

from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.ports import CatalogFilters
from papers2zim.sources.bibliothequenumeriqueromande.catalog import (
    ACQUISITION_REL,
    BASE_URL,
    BNR_LANGUAGE,
    BNR_SOURCE,
    COVER_RELS,
    EPUB_MEDIA_TYPE,
    BibliothequeNumeriqueRomandeCatalog,
    uuid_from_feed_id,
)

NAV_TYPE = "application/atom+xml;profile=opds-catalog;kind=navigation"

CONTES_ID = "urn:uuid:urn:uuid:87A3391F-6BF8-1014-9269-99B4F1E6D0DC"
CONTES_UUID = "87a3391f-6bf8-1014-9269-99b4f1e6d0dc"
CONTES_DESCRIPTION = (
    "Les contes de Perrault ont survécu depuis le 17e siècle et font, encore "
    "aujourd’hui, les délices des enfants comme des adultes."
)

VOLPONE_ID = "urn:uuid:bc04d2e4-10c3-4789-a2c1-749c63d2f125"
VOLPONE_UUID = "bc04d2e4-10c3-4789-a2c1-749c63d2f125"
VOLPONE_DESCRIPTION = (
    "Volpone (1605), l’un des chefs-d’œuvre de l’âge d’or du théâtre anglais, "
    "a pour protagoniste un personnage muet: l’or."
)


def _feed(*entries: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        f"{''.join(entries)}"
        "</feed>"
    )


def _nav_entry(entry_id: str, title: str, href: str) -> str:
    return (
        "<entry>"
        f"<title>{title}</title>"
        f"<id>{entry_id}</id>"
        f'<link rel="subsection" type="{NAV_TYPE}" href="{href}"/>'
        "</entry>"
    )


def _book(
    book_id: str,
    title: str,
    *,
    author: str = "Charles Perrault",
    categories: tuple[str, ...] = ("17e", "Conte", "Littérature française"),
    description: str = CONTES_DESCRIPTION,
    image_id: int = 449,
    data_id: int = 907,
) -> str:
    author_xml = f"<author><name>{author}</name></author>"
    categories_xml = "".join(
        f'<category term="{category}"/>' for category in categories
    )
    return (
        "<entry>"
        f"<title>{title}</title>"
        f"<id>{book_id}</id>"
        f'<content type="text/html">{description}</content>'
        f"{author_xml}"
        f"{categories_xml}"
        f'<link href="fetch.php?height=164&amp;id={image_id}" type="image/jpeg" '
        f'rel="{COVER_RELS[0]}"/>'
        f'<link href="fetch.php?data={data_id}&amp;type=epub&amp;id={image_id}" '
        f'type="{EPUB_MEDIA_TYPE}" rel="{ACQUISITION_REL}"/>'
        "</entry>"
    )


def _home() -> str:
    return _feed(
        _nav_entry("cops:series", "Series", "series.php"),
        _nav_entry("cops:authors", "Authors", "authors.php"),
        _nav_entry("cops:tags", "Tags", "tags.php"),
        _nav_entry("cops:books", "Books", "books.php"),
    )


class StubEngine(DownloadEngine):
    def __init__(self, pages: dict[str, str]):
        self.pages = pages
        self.fetched: list[str] = []

    def fetch_bytes(self, url: str) -> bytes:
        self.fetched.append(url)
        return self.pages[url].encode("utf-8")


def _catalog(
    pages: dict[str, str],
) -> tuple[BibliothequeNumeriqueRomandeCatalog, StubEngine]:
    engine = StubEngine({BASE_URL: _home(), **pages})
    return BibliothequeNumeriqueRomandeCatalog(engine, base_url=BASE_URL), engine


def test_discover_without_filter_reads_every_title_page():
    catalog, engine = _catalog(
        {
            "https://ebooks-bnr.com/opds/books.php": _feed(
                _nav_entry("title:c", "C", "books.php?prefix=C"),
                _nav_entry("title:v", "V", "books.php?prefix=V"),
            ),
            "https://ebooks-bnr.com/opds/books.php?prefix=C": _feed(
                _book(CONTES_ID, "CONTES")
            ),
            "https://ebooks-bnr.com/opds/books.php?prefix=V": _feed(
                _book(
                    VOLPONE_ID,
                    "Volpone",
                    author="Ben Jonson",
                    categories=("17e", "Littérature anglo-saxonne", "Théâtre"),
                    description=VOLPONE_DESCRIPTION,
                    image_id=1020,
                    data_id=680,
                )
            ),
        }
    )

    refs = list(catalog.discover(CatalogFilters()))

    assert [ref.id for ref in refs] == [CONTES_UUID, VOLPONE_UUID]
    first = refs[0]
    assert first.source == BNR_SOURCE
    assert first.extra["title"] == "CONTES"
    assert first.extra["author"] == "Charles Perrault"
    assert first.extra["categories"] == ["17e", "Conte", "Littérature française"]
    assert first.extra["description"] == CONTES_DESCRIPTION
    assert first.extra["languages"] == [BNR_LANGUAGE]
    assert first.extra["source_url"] == (
        "https://ebooks-bnr.com/opds/fetch.php?data=907&type=epub&id=449"
    )
    assert first.extra["cover_url"] == (
        "https://ebooks-bnr.com/opds/fetch.php?height=164&id=449"
    )
    assert refs[1].extra["author"] == "Ben Jonson"
    assert refs[1].extra["categories"] == [
        "17e",
        "Littérature anglo-saxonne",
        "Théâtre",
    ]
    assert refs[1].extra["description"] == VOLPONE_DESCRIPTION
    assert engine.fetched[0] == BASE_URL


def test_discover_returns_nothing_when_no_supported_format_requested():
    catalog, engine = _catalog({})

    assert list(catalog.discover(CatalogFilters(formats=["pdf"]))) == []
    assert engine.fetched == []


def test_discover_deduplicates_books_listed_across_categories():
    catalog, _ = _catalog(
        {
            "https://ebooks-bnr.com/opds/tags.php": _feed(
                _nav_entry("tag:conte", "Conte", "index.php?page=4&amp;id=1"),
                _nav_entry("tag:jeunesse", "Jeunesse", "index.php?page=4&amp;id=2"),
            ),
            "https://ebooks-bnr.com/opds/index.php?page=4&id=1": _feed(
                _book(CONTES_ID, "CONTES", categories=("Conte", "Jeunesse")),
                _book(
                    VOLPONE_ID,
                    "Volpone",
                    author="Ben Jonson",
                    categories=("Théâtre",),
                    description=VOLPONE_DESCRIPTION,
                    image_id=1020,
                    data_id=680,
                ),
            ),
            "https://ebooks-bnr.com/opds/index.php?page=4&id=2": _feed(
                _book(CONTES_ID, "CONTES", categories=("Conte", "Littérature")),
            ),
        }
    )

    refs = list(
        catalog.discover(CatalogFilters(options={"categories": ["Conte", "Jeunesse"]}))
    )

    assert [ref.id for ref in refs] == [CONTES_UUID, VOLPONE_UUID]
    # Only the first occurrence of a book is kept.
    assert refs[0].extra["categories"] == ["Conte", "Jeunesse"]
    assert refs[0].extra["title"] == "CONTES"


def test_discover_skips_entries_without_title_id_or_epub_link():
    catalog, _ = _catalog(
        {
            "https://ebooks-bnr.com/opds/books.php": _feed(
                _nav_entry("title:c", "C", "books.php?prefix=C")
            ),
            "https://ebooks-bnr.com/opds/books.php?prefix=C": _feed(
                _book(CONTES_ID, "CONTES"),
                "<entry><title>No id</title></entry>",
                "<entry><id>urn:uuid:missing-title</id></entry>",
                "<entry><title>No epub</title><id>urn:uuid:no-epub</id></entry>",
            ),
        }
    )

    refs = list(catalog.discover(CatalogFilters()))

    assert [ref.id for ref in refs] == [CONTES_UUID]


def test_list_authors_expands_the_alphabet_index():
    catalog, _ = _catalog(
        {
            "https://ebooks-bnr.com/opds/authors.php": _feed(
                _nav_entry("authors:a", "A", "authors.php?letter=A"),
                _nav_entry("authors:w", "W", "authors.php?letter=W"),
            ),
            "https://ebooks-bnr.com/opds/authors.php?letter=A": _feed(
                _nav_entry("author:1", "Austen Jane", "index.php?page=3&amp;id=1")
            ),
            "https://ebooks-bnr.com/opds/authors.php?letter=W": _feed(
                _nav_entry(
                    "author:419", "Wharton Edith", "index.php?page=3&amp;id=419"
                ),
                _nav_entry(
                    "author:421", "Wilde Percival", "index.php?page=3&amp;id=421"
                ),
            ),
        }
    )

    assert catalog.list_authors() == [
        "Austen Jane",
        "Wharton Edith",
        "Wilde Percival",
    ]


def test_discover_selects_books_by_uuid():
    catalog, _ = _catalog(
        {
            "https://ebooks-bnr.com/opds/books.php": _feed(
                _nav_entry("title:c", "C", "books.php?prefix=C")
            ),
            "https://ebooks-bnr.com/opds/books.php?prefix=C": _feed(
                _book(CONTES_ID, "CONTES"),
                _book(
                    VOLPONE_ID,
                    "Volpone",
                    author="Ben Jonson",
                    categories=("17e", "Littérature anglo-saxonne", "Théâtre"),
                    description=VOLPONE_DESCRIPTION,
                    image_id=1020,
                    data_id=680,
                ),
            ),
        }
    )

    for requested in (CONTES_UUID, CONTES_UUID.upper()):
        refs = list(catalog.discover(CatalogFilters(options={"book_ids": [requested]})))
        assert [ref.id for ref in refs] == [CONTES_UUID]


def test_uuid_from_feed_id_extracts_the_uuid():
    feed_id = "urn:uuid:AWP-93A150D8-630A-4B26-B495-2E848BB09B9E"

    assert uuid_from_feed_id(feed_id) == "93a150d8-630a-4b26-b495-2e848bb09b9e"


def test_uuid_from_feed_id_rejects_non_uuid_ids():
    with pytest.raises(ValueError):
        uuid_from_feed_id("urn:uuid:http://example.org/book")
