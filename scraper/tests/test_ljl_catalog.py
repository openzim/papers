"""Tests for Littérature jeunesse libre catalog discovery."""

import html

import pytest

from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.language import normalize_language
from papers2zim.core.opds import ACQUISITION_REL, COVER_RELS
from papers2zim.core.ports import CatalogFilters
from papers2zim.core.utils import CriticalError
from papers2zim.sources.litteraturejeunesselibre.catalog import (
    BASE_URL,
    EPUB_MEDIA_TYPE,
    FORMAT_BY_MEDIA_TYPE,
    LJL_SOURCE,
    PDF_MEDIA_TYPE,
    LitteratureJeunesseLibreCatalog,
)
from papers2zim.sources.litteraturejeunesselibre.categories import category_resolver

NAV_TYPE = "application/atom+xml;profile=opds-catalog"
FETCH_PATH = "/bbs/opds/fetch.php"

ANIMAUX_ID = "urn:uuid:urn:uuid:87A3391F-6BF8-1014-9269-99B4F1E6D0DC"
ANIMAUX_UUID = "87a3391f-6bf8-1014-9269-99b4f1e6d0dc"
ANIMAUX_DESCRIPTION = "Un album pour découvrir les animaux de la ferme."

CONTE_ID = "urn:uuid:bc04d2e4-10c3-4789-a2c1-749c63d2f125"
CONTE_UUID = "bc04d2e4-10c3-4789-a2c1-749c63d2f125"
CONTE_DESCRIPTION = "Un conte traditionnel illustré pour les jeunes lecteurs."

RAW_HTML_DESCRIPTION = (
    "TAGS: conte, domaine public, morale <div><div>Une petite fille moqueuse, "
    "une petite fille gourmande et une petite fille douillette partent se "
    "promener dans la forêt malgré les recommandations de leurs "
    "parents.</div><div><br></div>Extrait des Contes du Petit-Château.</div>"
)


def _feed(*entries: str, next_href: str | None = None) -> str:
    next_link = f'<link rel="next" href="{next_href}"/>' if next_href else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom" '
        'xmlns:dcterms="http://purl.org/dc/terms/">'
        f"{next_link}{''.join(entries)}"
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
    authors: tuple[str, ...] = ("Jeanne Auteur",),
    categories: tuple[str, ...] = ("chien", "conte"),
    description: str = ANIMAUX_DESCRIPTION,
    image_id: int = 449,
    data_id: int = 907,
    pdf: bool = True,
    language: str = "fra",
) -> str:
    authors_xml = "".join(f"<author><name>{name}</name></author>" for name in authors)
    categories_xml = "".join(
        f'<category term="{category}"/>' for category in categories
    )
    pdf_link = (
        f'<link href="{FETCH_PATH}?data={data_id}'
        f'&amp;type=pdf&amp;id={image_id}" '
        f'type="{PDF_MEDIA_TYPE}" rel="{ACQUISITION_REL}"/>'
        if pdf
        else ""
    )
    return (
        "<entry>"
        f"<title>{title}</title>"
        f"<id>{book_id}</id>"
        f'<content type="text/html">{html.escape(description)}</content>'
        f"{authors_xml}"
        f"{categories_xml}"
        f"<dcterms:language>{language}</dcterms:language>"
        f'<link href="{FETCH_PATH}?height=164&amp;id={image_id}" '
        f'type="image/jpeg" rel="{COVER_RELS[0]}"/>'
        f'<link href="{FETCH_PATH}?data={data_id}'
        f'&amp;type=epub&amp;id={image_id}" '
        f'type="{EPUB_MEDIA_TYPE}" rel="{ACQUISITION_REL}"/>'
        f"{pdf_link}"
        "</entry>"
    )


def _home() -> str:
    return _feed(
        _nav_entry("/bbs/opds/series", "Séries", "/bbs/opds/series"),
        _nav_entry("/bbs/opds/author", "Auteurs", "/bbs/opds/author"),
        _nav_entry("/bbs/opds/books", "Livres", "/bbs/opds/books"),
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
) -> tuple[LitteratureJeunesseLibreCatalog, StubEngine]:
    engine = StubEngine({BASE_URL: _home(), **pages})
    return LitteratureJeunesseLibreCatalog(engine, base_url=BASE_URL), engine


def test_discover_without_filter_reads_every_title_page():
    catalog, engine = _catalog(
        {
            f"{BASE_URL}/books": _feed(
                _nav_entry("books:a", "A", f"{BASE_URL}/books?start=A"),
                _nav_entry("books:c", "C", f"{BASE_URL}/books?start=C"),
            ),
            f"{BASE_URL}/books?start=A": _feed(_book(ANIMAUX_ID, "Animaux")),
            f"{BASE_URL}/books?start=C": _feed(
                _book(
                    CONTE_ID,
                    "Contes",
                    authors=("Pierre Conteur", "Marie Illustratrice"),
                    categories=("conte",),
                    description=CONTE_DESCRIPTION,
                    image_id=1020,
                    data_id=680,
                    pdf=False,
                )
            ),
        }
    )

    refs = list(catalog.discover(CatalogFilters()))

    assert [ref.id for ref in refs] == [ANIMAUX_UUID, CONTE_UUID]
    first = refs[0]
    assert first.source == LJL_SOURCE
    assert first.extra["title"] == "Animaux"
    assert first.extra["authors"] == ["Jeanne Auteur"]
    assert first.extra["categories"] == ["Animaux", "Contes & légendes"]
    assert first.extra["languages"] == ["fr"]
    assert first.extra["description"] == ANIMAUX_DESCRIPTION
    assert first.extra["cover_url"] == (
        "https://litterature-jeunesse-libre.fr/bbs/opds/fetch.php?height=164&id=449"
    )
    assert [(fmt.name, fmt.media_type) for fmt in first.extra["formats"]] == [
        ("epub", EPUB_MEDIA_TYPE),
        ("pdf", PDF_MEDIA_TYPE),
    ]
    assert first.extra["formats"][0].url == (
        "https://litterature-jeunesse-libre.fr/bbs/opds/fetch.php"
        "?data=907&type=epub&id=449"
    )
    assert refs[1].extra["authors"] == ["Pierre Conteur", "Marie Illustratrice"]
    assert refs[1].extra["categories"] == ["Contes & légendes"]
    assert [fmt.name for fmt in refs[1].extra["formats"]] == ["epub"]
    assert engine.fetched[0] == BASE_URL


def test_discover_cleans_html_descriptions_and_drops_the_tags_prefix():
    catalog, _ = _catalog(
        {
            f"{BASE_URL}/books": _feed(
                _nav_entry("books:a", "A", f"{BASE_URL}/books?start=A")
            ),
            f"{BASE_URL}/books?start=A": _feed(
                _book(ANIMAUX_ID, "Animaux", description=RAW_HTML_DESCRIPTION)
            ),
        }
    )

    refs = list(catalog.discover(CatalogFilters()))

    assert refs[0].extra["description"] == (
        "Une petite fille moqueuse, une petite fille gourmande et une petite "
        "fille douillette partent se promener dans la forêt malgré les "
        "recommandations de leurs parents. Extrait des Contes du "
        "Petit-Château."
    )


def test_discover_returns_nothing_when_no_supported_format_requested():
    catalog, engine = _catalog({})

    assert list(catalog.discover(CatalogFilters(formats=["html"]))) == []
    assert engine.fetched == []


def test_list_categories_returns_the_collapsed_collections():
    catalog, engine = _catalog({})

    assert catalog.list_categories() == sorted(
        category_resolver.order, key=str.casefold
    )
    # The list comes from the scraper, not from an LJL tags feed.
    assert engine.fetched == []


def test_discover_filters_by_collapsed_category():
    catalog, _ = _catalog(
        {
            f"{BASE_URL}/books": _feed(
                _nav_entry("books:a", "A", f"{BASE_URL}/books?start=A"),
            ),
            f"{BASE_URL}/books?start=A": _feed(
                _book(ANIMAUX_ID, "Animaux", categories=("chien",)),
                _book(
                    CONTE_ID,
                    "Contes",
                    categories=("conte",),
                    description=CONTE_DESCRIPTION,
                    image_id=1020,
                    data_id=680,
                ),
            ),
        }
    )

    refs = list(catalog.discover(CatalogFilters(options={"categories": ["animaux"]})))
    assert [ref.id for ref in refs] == [ANIMAUX_UUID]

    refs = list(
        catalog.discover(CatalogFilters(options={"categories": ["Contes & légendes"]}))
    )
    assert [ref.id for ref in refs] == [CONTE_UUID]


def test_discover_filters_unknown_tags_into_autres():
    catalog, _ = _catalog(
        {
            f"{BASE_URL}/books": _feed(
                _nav_entry("books:a", "A", f"{BASE_URL}/books?start=A"),
            ),
            f"{BASE_URL}/books?start=A": _feed(
                _book(ANIMAUX_ID, "Animaux", categories=("Nouvelle catégorie",)),
            ),
        }
    )

    refs = list(catalog.discover(CatalogFilters(options={"categories": ["Autres"]})))
    assert [ref.id for ref in refs] == [ANIMAUX_UUID]


def test_discover_rejects_unknown_categories():
    catalog, engine = _catalog({})

    with pytest.raises(CriticalError, match="Available categories"):
        list(catalog.discover(CatalogFilters(options={"categories": ["chien"]})))

    assert engine.fetched == []


def test_discover_skips_entries_without_title_id_or_download_link():
    catalog, _ = _catalog(
        {
            f"{BASE_URL}/books": _feed(
                _nav_entry("books:a", "A", f"{BASE_URL}/books?start=A")
            ),
            f"{BASE_URL}/books?start=A": _feed(
                _book(ANIMAUX_ID, "Animaux"),
                "<entry><title>No id</title></entry>",
                "<entry><id>urn:uuid:missing-title</id></entry>",
                "<entry><title>No link</title><id>urn:uuid:no-link</id></entry>",
            ),
        }
    )

    refs = list(catalog.discover(CatalogFilters()))

    assert [ref.id for ref in refs] == [ANIMAUX_UUID]


def test_list_authors_expands_the_alphabet_index():
    catalog, _ = _catalog(
        {
            f"{BASE_URL}/author": _feed(
                _nav_entry("authors:a", "A", f"{BASE_URL}/author?letter=A"),
                _nav_entry("authors:w", "W", f"{BASE_URL}/author?letter=W"),
            ),
            f"{BASE_URL}/author?letter=A": _feed(
                _nav_entry("author:1", "Austen Jane", "/bbs/opds/author?id=1")
            ),
            f"{BASE_URL}/author?letter=W": _feed(
                _nav_entry("author:419", "Wharton Edith", "/bbs/opds/author?id=419"),
                _nav_entry("author:421", "Wilde Percival", "/bbs/opds/author?id=421"),
            ),
        }
    )

    assert catalog.list_authors() == [
        "Austen Jane",
        "Wharton Edith",
        "Wilde Percival",
    ]


def test_discover_matches_authors_regardless_of_name_order_and_accents():
    catalog, _ = _catalog(
        {
            f"{BASE_URL}/author": _feed(
                _nav_entry("authors:b", "B", f"{BASE_URL}/author?letter=B"),
            ),
            f"{BASE_URL}/author?letter=B": _feed(
                _nav_entry("author:1", "Bousquet Joë", "/bbs/opds/author?id=1"),
            ),
            f"{BASE_URL}/author?id=1": _feed(
                _book(ANIMAUX_ID, "Animaux", authors=("Joë Bousquet",)),
            ),
        }
    )

    for requested in (
        "Joe Bousquet",
        "Bousquet Joe",
        "Bousquet, Joë",
        "Joë Bousquet",
    ):
        refs = list(catalog.discover(CatalogFilters(options={"authors": [requested]})))
        assert [ref.id for ref in refs] == [ANIMAUX_UUID]
        assert refs[0].extra["authors"] == ["Joë Bousquet"]


def test_discover_selects_books_by_uuid():
    catalog, _ = _catalog(
        {
            f"{BASE_URL}/books": _feed(
                _nav_entry("books:a", "A", f"{BASE_URL}/books?start=A")
            ),
            f"{BASE_URL}/books?start=A": _feed(
                _book(ANIMAUX_ID, "Animaux"),
                _book(
                    CONTE_ID,
                    "Contes",
                    categories=("conte",),
                    description=CONTE_DESCRIPTION,
                    image_id=1020,
                    data_id=680,
                ),
            ),
        }
    )

    for requested in (ANIMAUX_UUID, ANIMAUX_UUID.upper()):
        refs = list(catalog.discover(CatalogFilters(options={"book_ids": [requested]})))
        assert [ref.id for ref in refs] == [ANIMAUX_UUID]


def test_discover_follows_book_feed_pagination():
    second_page = f"{BASE_URL}/books?start=A&page=2"
    catalog, engine = _catalog(
        {
            f"{BASE_URL}/books": _feed(
                _nav_entry("books:a", "A", f"{BASE_URL}/books?start=A")
            ),
            f"{BASE_URL}/books?start=A": _feed(
                _book(ANIMAUX_ID, "Animaux"),
                next_href="/bbs/opds/books?start=A&amp;page=2",
            ),
            second_page: _feed(
                _book(
                    CONTE_ID,
                    "Contes",
                    categories=("conte",),
                    description=CONTE_DESCRIPTION,
                    image_id=1020,
                    data_id=680,
                )
            ),
        }
    )

    refs = list(catalog.discover(CatalogFilters()))

    assert [ref.id for ref in refs] == [ANIMAUX_UUID, CONTE_UUID]
    assert second_page in engine.fetched


def test_discover_stops_on_pagination_loop():
    feed_url = f"{BASE_URL}/books?start=A"
    catalog, engine = _catalog(
        {
            f"{BASE_URL}/books": _feed(
                _nav_entry("books:a", "A", f"{BASE_URL}/books?start=A")
            ),
            feed_url: _feed(
                _book(ANIMAUX_ID, "Animaux"),
                next_href="/bbs/opds/books?start=A",
            ),
        }
    )

    refs = list(catalog.discover(CatalogFilters()))

    assert [ref.id for ref in refs] == [ANIMAUX_UUID]
    assert engine.fetched.count(feed_url) == 1


def test_list_series_follows_navigation_pagination():
    catalog, engine = _catalog(
        {
            f"{BASE_URL}/series": _feed(
                _nav_entry("series:a", "A", f"{BASE_URL}/series?letter=A"),
                next_href="/bbs/opds/series?page=2",
            ),
            f"{BASE_URL}/series?page=2": _feed(
                _nav_entry("series:b", "B", f"{BASE_URL}/series?letter=B"),
            ),
            f"{BASE_URL}/series?letter=A": _feed(
                _nav_entry("series:1", "Série 1", "/bbs/opds/series?id=1"),
            ),
            f"{BASE_URL}/series?letter=B": _feed(
                _nav_entry("series:2", "Série 2", "/bbs/opds/series?id=2"),
            ),
        }
    )

    assert catalog.list_series() == ["Série 1", "Série 2"]
    assert f"{BASE_URL}/series?page=2" in engine.fetched


def test_list_titles_skips_the_all_navigation_entry():
    catalog, _ = _catalog(
        {
            f"{BASE_URL}/books": _feed(
                _nav_entry("books:all", "All", f"{BASE_URL}/books?all=1"),
                _nav_entry("books:a", "A", f"{BASE_URL}/books?start=A"),
            ),
        }
    )

    assert catalog.list_titles() == ["A"]


def test_supported_media_types_map_to_formats():
    assert FORMAT_BY_MEDIA_TYPE == {
        EPUB_MEDIA_TYPE: "epub",
        PDF_MEDIA_TYPE: "pdf",
    }


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("fra", "fr"),
        ("fre", "fr"),
        ("eng", "en"),
        ("fr", "fr"),
        ("FR", "fr"),
        ("grc", "grc"),
    ],
)
def test_normalize_language_returns_iso_639_1_codes(code, expected):
    assert normalize_language(code) == expected


def test_normalize_language_rejects_blank_values():
    assert normalize_language(None) is None
    assert normalize_language("  ") is None
