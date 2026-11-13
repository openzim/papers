"""Tests for OPDS-backed Wikisource discovery."""

import re
from unittest.mock import patch
from urllib.parse import unquote

import pytest

from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.ports import CatalogFilters
from papers2zim.core.utils import CriticalError
from papers2zim.sources.wikisource import catalog as catalog_module
from papers2zim.sources.wikisource.catalog import (
    WIKISOURCE_SOURCE,
    WikisourceCatalog,
    page_key,
)

BASE = "https://ws-export.wmcloud.org"

INDEX_HTML = """<html><body><h1>Index of /opds/en</h1>
<a href="/opds/">Parent Directory</a>
<a href="Ready_for_export.xml">Ready_for_export.xml</a>
</body></html>"""


def _entry(
    page: str, title: str, *, epub: bool = True, xhtml: bool = True, mobi: bool = False
) -> str:
    links = ""
    if epub:
        links += (
            '<link rel="http://opds-spec.org/acquisition" '
            'type="application/epub+zip" '
            f'href="{BASE}/?lang=en&amp;format=epub&amp;page={page}"/>'
        )
    if mobi:
        links += (
            '<link rel="http://opds-spec.org/acquisition" '
            'type="application/x-mobipocket-ebook" '
            f'href="{BASE}/?lang=en&amp;format=mobi&amp;page={page}"/>'
        )
    if xhtml:
        links += (
            '<link rel="http://opds-spec.org/acquisition" '
            'type="application/xhtml+xml" '
            f'href="{BASE}/?lang=en&amp;format=xhtml&amp;page={page}"/>'
        )
    return (
        '<entry xml:lang="en">'
        f"<title>{title}</title>"
        f'<id xsi:type="dcterms:URI">https://en.wikisource.org/wiki/{page}</id>'
        "<rights>http://creativecommons.org/licenses/by-sa/3.0</rights>"
        "<author><name>A. Writer</name></author>"
        '<dc:language xsi:type="dcterms:RFC4646">en</dc:language>'
        f'<dc:source xsi:type="dcterms:URI">https://en.wikisource.org/wiki/{page}</dc:source>'
        '<dcterms:issued xsi:type="dcterms:W3CDTF">1913</dcterms:issued>'
        f"{links}"
        "</entry>"
    )


def _feed(*entries: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/">'
        "<title>Category:Ready_for_export</title>"
        f"{''.join(entries)}"
        "</feed>"
    )


class StubEngine(DownloadEngine):
    def __init__(self, responses: dict[str, str]):
        self._responses = responses
        self.fetched: list[str] = []

    def fetch_bytes(self, url: str) -> bytes:
        self.fetched.append(url)
        for fragment, body in self._responses.items():
            if fragment in url:
                return body.encode("utf-8")
        raise AssertionError(f"unexpected fetch: {url}")


def _catalog(feed_body: str) -> tuple[WikisourceCatalog, StubEngine]:
    engine = StubEngine(
        {"/opds/en/Ready_for_export.xml": feed_body, "/opds/en/": INDEX_HTML}
    )
    return WikisourceCatalog(engine, base_url=BASE), engine


def test_discover_parses_feed_entries_into_work_refs():
    catalog, _ = _catalog(
        _feed(
            _entry("First_Book", "First Book"),
            _entry("Second_Book", "Second Book", xhtml=False),
        )
    )

    refs = list(catalog.discover(CatalogFilters(languages=["en"])))

    assert len(refs) == 2
    first = refs[0]
    assert first.source == WIKISOURCE_SOURCE
    assert first.extra["title"] == "First Book"
    assert first.extra["language"] == "en"
    assert first.extra["license"] == "http://creativecommons.org/licenses/by-sa/3.0"
    assert first.extra["author"] == "A. Writer"
    assert first.extra["issued"] == "1913"
    assert first.extra["source_url"] == "https://en.wikisource.org/wiki/First_Book"
    formats = {name: url for name, _mt, url in first.extra["formats"]}
    assert "epub" in formats
    assert formats["epub"].endswith("format=epub&page=First_Book")
    assert "xhtml" not in formats
    # second book advertises epub only
    assert [name for name, _mt, _url in refs[1].extra["formats"]] == ["epub"]


def test_discover_mints_path_safe_unique_ids():
    catalog, _ = _catalog(
        _feed(
            _entry("%27Tis_Sixty_Years_Since", chr(0x2019) + "Tis Sixty Years Since"),
            _entry("War_and_Peace/Chapter_1", "War and Peace"),
        )
    )

    refs = list(catalog.discover(CatalogFilters(languages=["en"])))

    ids = [ref.id for ref in refs]
    assert len(set(ids)) == len(ids)
    for work_id in ids:
        assert re.fullmatch(r"[a-z0-9_-]+", work_id), work_id
        assert work_id.startswith("en_")


def test_discover_keeps_non_latin_page_names_readable():
    catalog, _ = _catalog(_feed(_entry("%E7%B4%85%E6%A8%93%E5%A4%A2", "紅樓夢")))

    refs = list(catalog.discover(CatalogFilters(languages=["en"])))

    assert refs[0].id.startswith("en_紅樓夢-")


def test_discover_requires_at_least_one_language():
    catalog, _ = _catalog(_feed(_entry("First_Book", "First Book")))

    with pytest.raises(CriticalError):
        list(catalog.discover(CatalogFilters()))


def test_discover_fails_when_a_requested_format_is_not_advertised():
    catalog, _ = _catalog(_feed(_entry("First_Book", "First Book")))

    with pytest.raises(CriticalError, match="html"):
        list(catalog.discover(CatalogFilters(languages=["en"], formats=["html"])))


def test_discover_fails_when_any_requested_format_is_not_advertised():
    catalog, _ = _catalog(_feed(_entry("First_Book", "First Book")))

    with pytest.raises(CriticalError, match="pdf"):
        list(
            catalog.discover(CatalogFilters(languages=["en"], formats=["epub", "pdf"]))
        )


def test_discover_does_not_fail_when_all_requested_formats_are_advertised():
    catalog, _ = _catalog(_feed(_entry("First_Book", "First Book")))

    refs = list(catalog.discover(CatalogFilters(languages=["en"], formats=["epub"])))

    assert len(refs) == 1
    assert refs[0].id.startswith("en_first-book")


def test_discover_error_names_the_available_formats():
    catalog, _ = _catalog(_feed(_entry("First_Book", "First Book")))

    with pytest.raises(CriticalError, match="ws-export offers: epub"):
        list(catalog.discover(CatalogFilters(languages=["en"], formats=["html"])))


def test_discover_skips_entries_missing_the_requested_format():
    catalog, _ = _catalog(
        _feed(
            _entry("First_Book", "First Book"),
            _entry("Second_Book", "Second Book", epub=False, mobi=True),
        )
    )

    refs = list(catalog.discover(CatalogFilters(languages=["en"], formats=["epub"])))

    assert len(refs) == 1
    assert refs[0].id.startswith("en_first-book")


def test_discover_ignores_unknown_acquisition_media_types():
    entry = _entry("First_Book", "First Book", xhtml=False).replace(
        "</entry>",
        '<link rel="http://opds-spec.org/acquisition" '
        'type="application/vnd.oasis.opendocument.text" '
        f'href="{BASE}/?lang=en&amp;format=odt&amp;page=First_Book"/>'
        "</entry>",
    )
    catalog, _ = _catalog(_feed(entry))

    (ref,) = list(catalog.discover(CatalogFilters(languages=["en"])))

    assert [name for name, _mt, _url in ref.extra["formats"]] == ["epub"]


def test_discover_ignores_mobi_links():
    catalog, _ = _catalog(
        _feed(
            _entry("First_Book", "First Book", mobi=True),
            _entry("Second_Book", "Second Book", epub=False, mobi=True),
        )
    )

    refs = list(catalog.discover(CatalogFilters(languages=["en"])))

    # mobi can never be requested, so a mobi-only entry has nothing to download
    assert len(refs) == 1
    assert [name for name, _mt, _url in refs[0].extra["formats"]] == ["epub"]


def test_discover_error_does_not_offer_mobi():
    catalog, _ = _catalog(_feed(_entry("First_Book", "First Book", mobi=True)))

    with pytest.raises(CriticalError, match=r"ws-export offers: epub\.$"):
        list(catalog.discover(CatalogFilters(languages=["en"], formats=["html"])))


def test_discover_selects_by_catalog_position():
    catalog, _ = _catalog(
        _feed(
            _entry("First_Book", "First Book"),
            _entry("Second_Book", "Second Book"),
            _entry("Third_Book", "Third Book"),
        )
    )

    refs = list(catalog.discover(CatalogFilters(languages=["en"], book_ids=["2"])))

    assert [ref.extra["title"] for ref in refs] == ["Second Book"]


@pytest.mark.parametrize(
    "name",
    [
        "%27Tis_Sixty_Years_Since",
        "'Tis Sixty Years Since",
        " 'Tis_Sixty Years_Since ",
    ],
)
def test_page_key_matches_url_and_display_forms(name):
    assert page_key(name) == "'Tis_Sixty_Years_Since"


def test_discover_selects_by_page_name_in_feed_order():
    catalog, _ = _catalog(
        _feed(
            _entry("First_Book", "First Book"),
            _entry("%27Tis_Sixty_Years_Since", "Tis Sixty Years Since"),
            _entry("Frankenstein%2C_or_the_Modern_Prometheus", "Frankenstein"),
        )
    )

    refs = list(
        catalog.discover(
            CatalogFilters(
                languages=["en"],
                options={
                    "pages": [
                        "Frankenstein,_or_the_Modern_Prometheus",
                        "'Tis_Sixty_Years_Since",
                    ]
                },
            )
        )
    )

    assert [ref.extra["title"] for ref in refs] == [
        "Tis Sixty Years Since",
        "Frankenstein",
    ]


def test_discover_warns_about_pages_missing_from_the_feed():
    catalog, _ = _catalog(_feed(_entry("First_Book", "First Book")))

    with patch.object(catalog_module.logger, "warning") as warning:
        refs = list(
            catalog.discover(
                CatalogFilters(
                    languages=["en"], options={"pages": ["First_Book", "No_Such_Book"]}
                )
            )
        )

    assert [ref.extra["title"] for ref in refs] == ["First Book"]
    warning.assert_called_once()
    assert "No_Such_Book" in warning.call_args.args


ONE_BOOK = _feed(_entry("First_Book", "First Book"))
ANOTHER_BOOK = _feed(_entry("Second_Book", "Second Book"))


def _feeds_catalog(feeds: dict[str, str]) -> tuple[WikisourceCatalog, StubEngine]:
    """A language directory advertising `feeds`, mapping file name to body."""
    responses = {f"/opds/en/{name}": body for name, body in feeds.items()}
    responses["/opds/en/"] = (
        "<html><body>"
        + "".join(f'<a href="{name}">{name}</a>' for name in feeds)
        + "</body></html>"
    )
    engine = StubEngine(responses)
    return WikisourceCatalog(engine, base_url=BASE), engine


TWO_FEEDS = {"Ready_for_export.xml": ONE_BOOK, "Not_ready.xml": ANOTHER_BOOK}


def test_discover_stops_when_the_directory_advertises_several_feeds():
    catalog, engine = _feeds_catalog(TWO_FEEDS)

    with pytest.raises(CriticalError, match="--wikisource-feed"):
        list(catalog.discover(CatalogFilters(languages=["en"])))

    assert [url for url in engine.fetched if url.endswith(".xml")] == []


def test_error_on_several_feeds_names_them_after_decoding():
    encoded = "%E0%A6%AA%E0%A6%BE%E0%A6%A0.xml"
    catalog, _ = _feeds_catalog(
        {"Ready_for_export.xml": ONE_BOOK, encoded: ANOTHER_BOOK}
    )

    with pytest.raises(CriticalError) as raised:
        list(catalog.discover(CatalogFilters(languages=["en"])))

    message = str(raised.value)
    assert unquote(encoded) in message
    assert encoded not in message


def test_discover_reads_only_the_feed_pinned_with_wikisource_feed():
    catalog, engine = _feeds_catalog(TWO_FEEDS)

    refs = list(
        catalog.discover(
            CatalogFilters(languages=["en"], options={"feed": "Not_ready.xml"})
        )
    )

    assert [ref.extra["title"] for ref in refs] == ["Second Book"]
    assert f"{BASE}/opds/en/Not_ready.xml" in engine.fetched
    assert f"{BASE}/opds/en/Ready_for_export.xml" not in engine.fetched


@pytest.mark.parametrize(
    "pinned",
    ["Not_ready.xml", "Not_ready", "/opds/en/Not_ready.xml", "not_ready.XML"],
)
def test_feed_pin_accepts_a_name_a_url_or_a_bare_stem(pinned: str):
    catalog, _ = _feeds_catalog(TWO_FEEDS)

    refs = list(
        catalog.discover(CatalogFilters(languages=["en"], options={"feed": pinned}))
    )

    assert [ref.extra["title"] for ref in refs] == ["Second Book"]


def test_feed_pin_that_matches_nothing_names_what_does():
    catalog, _ = _feeds_catalog(TWO_FEEDS)

    with pytest.raises(CriticalError, match=re.escape("Ready_for_export.xml")):
        list(
            catalog.discover(
                CatalogFilters(languages=["en"], options={"feed": "No_such_feed.xml"})
            )
        )


def test_feed_pin_on_a_language_without_feeds_fails_loudly():
    engine = StubEngine({"/opds/en/": "<html><body>no feed here</body></html>"})
    catalog = WikisourceCatalog(engine, base_url=BASE)

    with pytest.raises(CriticalError, match="no feed is advertised"):
        list(catalog.discover(CatalogFilters(languages=["en"], options={"feed": "X"})))


def test_discover_stops_when_the_feed_is_not_an_opds_feed():
    engine = StubEngine(
        {
            "/opds/en/Ready_for_export.xml": (
                "<html><body>Error 404: No route found</body></html>"
            ),
            "/opds/en/": INDEX_HTML,
        }
    )
    catalog = WikisourceCatalog(engine, base_url=BASE)

    with pytest.raises(CriticalError, match="not an OPDS feed"):
        list(catalog.discover(CatalogFilters(languages=["en"])))


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        ("Bon_pour_export.xml", "bon_pour_export"),
        ("bon_pour_export.XML", "bon_pour_export"),
        ("Bon_pour_export", "bon_pour_export"),
        (
            "https://ws-export.wmcloud.org/opds/fr/Bon_pour_export.xml",
            "bon_pour_export",
        ),
        ("%E0%A6%AA%E0%A6%BE%E0%A6%A0.xml", "\u09aa\u09be\u09a0"),
    ],
)
def test_feed_key_compares_bare_decoded_names(reference: str, expected: str):
    assert catalog_module.feed_key(reference) == expected
