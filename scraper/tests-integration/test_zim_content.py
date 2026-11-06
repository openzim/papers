"""End-to-end checks for the small ZIMs produced in CI."""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import pytest
from zimscraperlib.zim import Archive


@dataclass(frozen=True)
class ZimExpectation:
    """Expected source data for one generated integration-test ZIM."""

    filename: str
    title: str
    source_slug: str
    source_creator: str
    work_id: str
    format_name: str
    mimetype: str


ZIM_EXPECTATIONS = (
    ZimExpectation(
        filename="gutenberg-integration.zim",
        title="Gutenberg Test",
        source_slug="gutenberg",
        source_creator="gutenberg.org",
        work_id="11",
        format_name="html",
        mimetype="text/html",
    ),
    ZimExpectation(
        filename="opentextbooks-integration.zim",
        title="OTL Test",
        source_slug="opentextbooks",
        source_creator="open.umn.edu",
        work_id="54",
        format_name="pdf",
        mimetype="application/pdf",
    ),
    ZimExpectation(
        filename="onemorelibrary-integration.zim",
        title="One More Library Test",
        source_slug="onemorelibrary",
        source_creator="onemorelibrary.com",
        work_id="4077",
        format_name="epub",
        mimetype="application/epub+zip",
    ),
    pytest.param(
        ZimExpectation(
            filename="wikisource-integration.zim",
            title="Wikisource Test",
            source_slug="wikisource",
            source_creator="wikisource.org",
            work_id="en_tis-sixty-years-since-9cd9266e",
            format_name="epub",
            mimetype="application/epub+zip",
        ),
        marks=pytest.mark.skip(
            reason="wikisource ZIM is not built in CI: ws-export is unreachable"
        ),
    ),
)


def _read_json(zim: Archive, path: str) -> dict:
    item = zim.get_item(path)
    assert item
    assert item.mimetype == "application/json"
    return json.loads(bytes(item.content))


@pytest.fixture(params=ZIM_EXPECTATIONS, ids=lambda expected: expected.source_slug)
def expected(request) -> ZimExpectation:
    return request.param


@pytest.fixture
def zim_path(expected: ZimExpectation) -> Path:
    return Path(os.environ["ZIM_DIRECTORY"]) / expected.filename


@pytest.fixture
def zim(zim_path: Path) -> Archive:
    assert zim_path.is_file()
    return Archive(zim_path)


def test_zim_metadata_and_main_page(zim: Archive, expected: ZimExpectation):
    """The generated archive identifies its source and opens the UI."""
    assert zim.main_entry.is_redirect
    assert zim.main_entry.get_redirect_entry().path == "index.html"
    assert zim.get_text_metadata("Title") == expected.title
    assert zim.get_text_metadata("Creator") == expected.source_creator
    assert zim.get_text_metadata("Publisher") == "openZIM"
    assert "papers2zim-" in zim.get_text_metadata("Scraper")
    for path, mimetype in (
        ("favicon.svg", "image/svg+xml"),
        ("favicon.ico", "image/vnd.microsoft.icon"),
        ("apple-touch-icon.png", "image/png"),
        ("web-app-manifest-192x192.png", "image/png"),
        ("web-app-manifest-512x512.png", "image/png"),
        ("site.webmanifest", "application/manifest+json"),
    ):
        item = zim.get_item(path)
        assert item
        assert item.mimetype == mimetype
        assert len(item.content) > 0


def test_zim_contains_the_selected_work(zim: Archive, expected: ZimExpectation):
    """The UI data and requested source edition are present and readable."""
    config = _read_json(zim, "config.json")
    books = _read_json(zim, "books.json")

    assert config["source"]["slug"] == expected.source_slug
    assert books["totalCount"] == 1
    books_page = _read_json(zim, "books-pages/popularity/0.json")
    book_id = books_page["books"][0]["id"]
    assert re.fullmatch(r"[\w-]+", book_id), book_id
    assert books_page["books"][0]["availableFormats"] == [expected.format_name]
    book = _read_json(zim, f"books/{book_id}.json")
    assert book["id"] == book_id

    (format_info,) = [
        format_info
        for format_info in book["formats"]
        if format_info["format"] == expected.format_name
    ]
    assert format_info["available"] is True
    edition = zim.get_item(format_info["path"])
    assert edition
    assert edition.mimetype == expected.mimetype
    assert len(edition.content) > 0


def test_book_search_entry_links_by_source_id(zim: Archive, expected: ZimExpectation):
    """The search entry written while processing still reaches the book."""
    preview = _read_json(zim, "books-pages/popularity/0.json")["books"][0]
    search_entry = bytes(zim.get_item(f"index/book_{expected.work_id}").content)

    assert f"#/book/{expected.work_id}".encode() in search_entry
    assert _read_json(zim, f"books/{expected.work_id}.json")["id"] == preview["id"]


def test_edition_links_reach_the_ui_data(zim: Archive, expected: ZimExpectation):
    """A mirrored edition still opens the detail page of its own book."""
    if expected.format_name != "html":
        pytest.skip("only an HTML edition links back to the UI")
    preview = _read_json(zim, "books-pages/popularity/0.json")["books"][0]
    book = _read_json(zim, f"books/{preview['id']}.json")
    (edition,) = [item for item in book["formats"] if item["format"] == "html"]
    edition_html = bytes(zim.get_item(edition["path"]).content)

    link = re.search(rb"#/book/([\w-]+)", edition_html)
    assert link
    assert link[1].decode() == expected.work_id
    assert _read_json(zim, f"books/{expected.work_id}.json")["id"] == preview["id"]
