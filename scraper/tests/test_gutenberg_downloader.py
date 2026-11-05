"""Tests for the Gutenberg per-format download validation (#135)."""

from typing import cast

import pytest
import requests

from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.models import Work
from papers2zim.core.work_store import WorkStore
from papers2zim.sources.gutenberg.downloader import BookContent, download_book

MIRROR = "https://mirror.example"
BOOK_ID = "2202"
HTML = b"<html><body><p>Book content</p></body></html>"
# an HTML error page served for a book file URL, as reported in #135
JUNK = b"<!doctype html><html><head><title>500</title></head><body></body></html>"


class RecordingEngine:
    """Serves fixed content per file name; any other file 404s like the mirror"""

    def __init__(self, content_by_fname: dict[str, bytes]):
        self._content_by_fname = content_by_fname
        self.requested_urls: list[str] = []

    def fetch_bytes(self, url: str) -> bytes:
        self.requested_urls.append(url)
        for fname, content in self._content_by_fname.items():
            if url.endswith(f"/{fname}"):
                return content
        response = requests.Response()
        response.status_code = 404
        response.url = url
        raise requests.HTTPError(f"404 for {url}", response=response)


def _work() -> Work:
    return Work(
        id=BOOK_ID,
        source="gutenberg",
        title="Travels in the Great Desert of Sahara",
        languages=["en"],
        extra={"has_cover": False},
    )


def _download(
    work: Work, formats: list[str], **contents
) -> tuple[BookContent | None, WorkStore, RecordingEngine]:
    store = WorkStore()
    store.add(work)
    engine = RecordingEngine(contents)
    content = download_book(
        mirror_url=MIRROR,
        work=work,
        formats=formats,
        work_store=store,
        engine=cast(DownloadEngine, engine),
    )
    return content, store, engine


@pytest.mark.parametrize("book_format", ["epub", "pdf"])
def test_junk_content_is_never_stored_as_a_book_file(book_format):
    """A mirror failure served as HTML with a 200 status must not be kept"""
    work = _work()
    junk_fname = f"pg{BOOK_ID}.epub" if book_format == "epub" else f"pg{BOOK_ID}.pdf"
    content, store, _ = _download(
        work, ["html", book_format], **{junk_fname: JUNK, f"pg{BOOK_ID}.html": HTML}
    )

    assert content is not None
    assert content.files == {f"{BOOK_ID}.html": HTML}
    assert work.extra["unsupported_formats"] == [book_format]
    # the book survives on the formats that are actually readable
    assert store.get("gutenberg", BOOK_ID) is work


def test_all_candidates_of_a_format_are_probed_before_giving_up():
    work = _work()
    content, store, engine = _download(work, ["epub"], **{f"pg{BOOK_ID}.epub": JUNK})

    assert [
        url.rsplit("/", 1)[-1] for url in engine.requested_urls if ".epub" in url
    ] == [
        f"pg{BOOK_ID}-images-3.epub",
        f"pg{BOOK_ID}-images.epub",
        f"pg{BOOK_ID}.epub",
    ]
    # nothing readable at all: the book is dropped, as before
    assert content is None
    assert store.get("gutenberg", BOOK_ID) is None


def test_valid_epub_is_stored(make_epub):
    work = _work()
    epub = make_epub()
    content, store, _ = _download(
        work, ["epub"], **{f"pg{BOOK_ID}.epub": epub, f"pg{BOOK_ID}.html": HTML}
    )

    assert content is not None
    # HTML is always fetched alongside, as the ZIM's base format
    assert content.files == {f"{BOOK_ID}.epub": epub, f"{BOOK_ID}.html": HTML}
    assert work.extra["unsupported_formats"] == []
    assert store.get("gutenberg", BOOK_ID) is work


def test_empty_preferred_epub_falls_back_to_the_readable_one(make_epub):
    """The #2202 case: a 0-byte epub.images served with a 200 status"""
    work = _work()
    epub = make_epub()
    content, store, engine = _download(
        work,
        ["epub"],
        **{
            f"pg{BOOK_ID}-images.epub": b"",
            f"pg{BOOK_ID}.epub": epub,
            f"pg{BOOK_ID}.html": HTML,
        },
    )

    assert [
        url.rsplit("/", 1)[-1] for url in engine.requested_urls if ".epub" in url
    ] == [
        f"pg{BOOK_ID}-images-3.epub",
        f"pg{BOOK_ID}-images.epub",
        f"pg{BOOK_ID}.epub",
    ]
    assert content is not None
    assert content.files == {f"{BOOK_ID}.epub": epub, f"{BOOK_ID}.html": HTML}
    assert work.extra["unsupported_formats"] == []
    assert store.get("gutenberg", BOOK_ID) is work
