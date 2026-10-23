"""Tests for One More Library catalog discovery."""

from pathlib import Path

import pytest

from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.ports import CatalogFilters
from papers2zim.core.utils import CriticalError
from papers2zim.sources.onemorelibrary.catalog import (
    CATALOG_FILENAME,
    OML_SOURCE,
    OnemorelibraryCatalog,
    parse_listing,
)

LISTING_URL = "https://onemorelibrary.com/index.php/en/books"


def _card(
    book_id: int, title: str, slug: str, category: str, author: str, category_name: str
) -> str:
    return f"""
    <div class="item_box">
      <div class="item_img"><a
        href="/index.php/en/books/arts/book/{category}/{slug}-{book_id}">
        <img src="/components/com_djclassifieds/images/item/{book_id}_{slug}_thm.jpg" />
      </a></div>
      <div class="blog_det">
        <div class="title"><h2>
          <a
            href="/index.php/en/books/arts/book/{category}/{slug}-{book_id}">{title}</a></h2>
          <span class="type_button">
            <a href="/index.php/en/books?se=1&amp;re=1">English</a></span>
        </div>
        <div class="category">
          <a href="/index.php/en/books/arts/{category}">{category_name}</a></div>
        <div class="author_blog"><a class="author_blog_link"
          href="/index.php/en/books?se=1&amp;re=1">%AUTHOR% · English</a></div>
      </div>
    </div>
    """.replace("%AUTHOR%", author)


def _listing(*cards: str, starts: list[int] | None = None) -> str:
    pagination = "".join(
        f'<a href="{LISTING_URL}?start={start}">{start}</a>'
        for start in (starts if starts is not None else [])
    )
    return f"<html><body>{''.join(cards)}{pagination}</body></html>"


class StubEngine(DownloadEngine):
    def __init__(self, pages: dict[str, str] | None = None):
        self.pages = pages or {}
        self.downloaded: list[str] = []

    def fetch_bytes(self, url, headers=None):
        del headers
        self.downloaded.append(url)
        return self.pages[url].encode("utf-8")


def test_parse_listing_extracts_book_fields():
    html = _listing(_card(2833, "On Beauty", "on-beauty", "art-232", "Arthur", "Art"))

    (book,) = parse_listing(html, "https://onemorelibrary.com")

    assert book.id == "2833"
    assert book.title == "On Beauty"
    assert book.source_url.endswith("/on-beauty-2833")
    assert book.category_name == "Art"
    assert book.category_id == "art-232"
    assert book.author == "Arthur"
    assert book.language == "en"
    assert book.language_name == "English"


def test_discover_crawls_every_advertised_page():
    page0 = _listing(
        _card(1, "First", "first", "art-232", "A", "Art"),
        starts=[0, 32, 64],
    )
    page32 = _listing(_card(2, "Second", "second", "art-232", "B", "Art"))
    page64 = _listing(_card(3, "Third", "third", "art-232", "C", "Art"))
    engine = StubEngine(
        {
            f"{LISTING_URL}?start=0": page0,
            f"{LISTING_URL}?start=32": page32,
            f"{LISTING_URL}?start=64": page64,
        }
    )
    catalog = OnemorelibraryCatalog(engine)

    refs = list(catalog.discover(CatalogFilters()))

    assert [ref.id for ref in refs] == ["1", "2", "3"]
    assert all(ref.source == OML_SOURCE for ref in refs)
    assert engine.downloaded == [
        f"{LISTING_URL}?start=0",
        f"{LISTING_URL}?start=32",
        f"{LISTING_URL}?start=64",
    ]


def test_discover_merges_pagination_windows_revealed_by_later_pages():
    page0 = _listing(
        _card(1, "First", "first", "art-232", "A", "Art"),
        starts=[0, 32, 96],
    )
    page32 = _listing(
        _card(2, "Second", "second", "art-232", "B", "Art"),
        starts=[0, 32, 64, 96],
    )
    page64 = _listing(
        _card(3, "Third", "third", "art-232", "C", "Art"),
        starts=[0, 64, 96],
    )
    page96 = _listing(
        _card(4, "Fourth", "fourth", "art-232", "D", "Art"),
        starts=[0, 96],
    )
    engine = StubEngine(
        {
            f"{LISTING_URL}?start=0": page0,
            f"{LISTING_URL}?start=32": page32,
            f"{LISTING_URL}?start=64": page64,
            f"{LISTING_URL}?start=96": page96,
        }
    )
    catalog = OnemorelibraryCatalog(engine)

    refs = list(catalog.discover(CatalogFilters()))

    assert [ref.id for ref in refs] == ["1", "2", "3", "4"]
    assert engine.downloaded == [
        f"{LISTING_URL}?start=0",
        f"{LISTING_URL}?start=32",
        f"{LISTING_URL}?start=64",
        f"{LISTING_URL}?start=96",
    ]


def test_discover_explicit_ids_and_positions_ignore_language_and_category_filters():
    html = _listing(
        _card(10, "First", "first", "art-232", "A", "Art"),
        _card(20, "Second", "second", "science-204", "B", "Science"),
    )
    engine = StubEngine({f"{LISTING_URL}?start=0": html})
    catalog = OnemorelibraryCatalog(engine)

    assert [
        ref.id
        for ref in catalog.discover(
            CatalogFilters(
                languages=["fr"],
                collections=["science"],
                options={"book_ids": ["10"]},
            )
        )
    ] == ["10"]
    assert [
        ref.id
        for ref in catalog.discover(
            CatalogFilters(
                languages=["fr"],
                collections=["science"],
                book_ids=["1"],
            )
        )
    ] == ["10"]


def test_discover_filters_by_language_and_category():
    html = _listing(
        _card(1, "English Art", "english-art", "art-232", "A", "Art"),
        _card(2, "English Science", "english-science", "science-204", "B", "Science"),
    )
    engine = StubEngine({f"{LISTING_URL}?start=0": html})
    catalog = OnemorelibraryCatalog(engine)

    assert [
        ref.id
        for ref in catalog.discover(
            CatalogFilters(languages=["en"], collections=["art"])
        )
    ] == ["1"]


def test_discover_returns_nothing_when_no_supported_format_requested():
    engine = StubEngine()
    catalog = OnemorelibraryCatalog(engine)

    assert list(catalog.discover(CatalogFilters(formats=["html"]))) == []
    assert engine.downloaded == []


def test_discover_selects_exact_ids_and_positions():
    html = _listing(
        _card(10, "First", "first", "art-232", "A", "Art"),
        _card(20, "Second", "second", "art-232", "B", "Art"),
    )
    engine = StubEngine({f"{LISTING_URL}?start=0": html})
    catalog = OnemorelibraryCatalog(engine)

    assert [
        ref.id for ref in catalog.discover(CatalogFilters(options={"book_ids": ["20"]}))
    ] == ["20"]
    assert [ref.id for ref in catalog.discover(CatalogFilters(book_ids=["1"]))] == [
        "10"
    ]


def test_list_categories_returns_unique_sorted_pairs():
    html = _listing(
        _card(1, "One", "one", "art-232", "A", "Art"),
        _card(2, "Two", "two", "science-204", "B", "Science"),
        _card(3, "Three", "three", "art-232", "C", "Art"),
    )
    engine = StubEngine({f"{LISTING_URL}?start=0": html})
    catalog = OnemorelibraryCatalog(engine)

    assert catalog.list_categories() == [
        ("Art", "art-232"),
        ("Science", "science-204"),
    ]


def test_discover_reuses_and_writes_the_catalog_cache(tmp_path: Path):
    html = _listing(_card(1, "One", "one", "art-232", "A", "Art"))
    engine = StubEngine({f"{LISTING_URL}?start=0": html})
    catalog = OnemorelibraryCatalog(engine, cache_dir=tmp_path)

    first = list(catalog.discover(CatalogFilters()))
    engine.downloaded.clear()
    second = list(catalog.discover(CatalogFilters()))

    assert [ref.id for ref in first] == [ref.id for ref in second] == ["1"]
    assert engine.downloaded == []
    assert (tmp_path / CATALOG_FILENAME).exists()


def test_refresh_oml_catalog_requires_a_cache_dir():
    catalog = OnemorelibraryCatalog(StubEngine())

    with pytest.raises(
        CriticalError, match="--refresh-oml-catalog requires --cache-dir"
    ):
        catalog.refresh()
