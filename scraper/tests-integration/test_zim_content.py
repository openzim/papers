"""End-to-end checks for the small ZIMs produced in CI."""

import json
import os
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
    favicon = zim.get_item("favicon.png")
    assert favicon
    assert favicon.mimetype == "image/png"
    assert len(favicon.content) > 0


def test_zim_contains_the_selected_work(zim: Archive, expected: ZimExpectation):
    """The UI data and requested source edition are present and readable."""
    config = _read_json(zim, "config.json")
    books = _read_json(zim, "books.json")
    book = _read_json(zim, f"books/{expected.work_id}.json")

    assert config["source"]["slug"] == expected.source_slug
    assert books["totalCount"] == 1
    assert books["books"][0]["id"] == expected.work_id
    assert books["books"][0]["availableFormats"] == [expected.format_name]
    assert book["id"] == expected.work_id

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
