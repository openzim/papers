"""Tests for One More Library book-page metadata parsing."""

from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.ports import WorkRef
from papers2zim.sources.onemorelibrary.metadata import (
    OnemorelibraryMetadata,
    parse_book_page,
)

PAGE_URL = (
    "https://onemorelibrary.com/index.php/en/books/arts/book/art-232/on-beauty-2833"
)

BOOK_PAGE = """
<html><head>
  <meta property="og:image"
    content="/components/com_djclassifieds/images/item/2833_cover.png" />
</head><body>
  <div class="title_top info"><h1>On the Comparative Place of Interest</h1>
    <span class="type_button">English</span></div>
  <div class="additional">
    <div class="row"><span class="row_label">In categories:</span>
      <span class="row_value">
        <a href="/index.php/en/books/arts/art-232">Art</a>,
        <a href="/index.php/en/books/major-collections/schopenhauer-359">
          Schopenhauer Collection</a>
      </span></div>
    <div class="row"><span class="row_label">Book ID:</span>
      <span class="row_value">2833</span></div>
  </div>
  <div class="general_det">
    <div class="profile_name_data"><h2>
      <a class="profile_name"
        href="/index.php/en/search-results/author/arthur-schopenhauer-358">Arthur
        Schopenhauer <span>(79</span> <span>books)</span></a>
    </h2></div>
    <div class="row_wikipedia">
      <a href="http://wikipedia.org/wiki/Arthur_Schopenhauer">wiki</a></div>
  </div>
  <div class="custom_det">
    <div class="row"><h3><span class="row_label">Year of first publication:</span>
      <span class="row_value">1851</span></h3></div>
    <div class="row"><h3><span class="row_label">Translator:</span>
      <span class="row_value">T. Bailey Saunders</span></h3></div>
    <div class="row"><h3><span class="row_label">License:</span>
      <span class="row_value">CC BY-SA 4.0</span></h3></div>
    <div class="row"><h3><span class="row_label">Edition:</span>
      <span class="row_value">A. L. Burt Company</span></h3></div>
  </div>
  <div class="additional attachments files-def"><h2>Book files</h2>
    <div class="row">
      <div class="row">
        <a href="https://onemorelibrary.com/index.php?view=download&amp;fid=14599">
        <span>On the Comparative - EPUB</span><br/>
        <span class="djc_filesize">epub | 9.72 KB | 440 hits</span></a></div>
      <div class="row">
        <a href="https://onemorelibrary.com/index.php?view=download&amp;fid=14598">
        <span>On the Comparative - PDF</span><br/>
        <span class="djc_filesize">pdf | 84.21 KB | 1226 hits</span></a></div>
      <div class="row">
        <a href="https://onemorelibrary.com/index.php?view=download&amp;fid=14600">
        <span>On the Comparative - MOBI</span><br/>
        <span class="djc_filesize">mobi | 20.47 KB | 352 hits</span></a></div>
    </div>
  </div>
  <img id="djc_mainimage"
    src="/components/com_djclassifieds/images/item/2833_main.png" />
</body></html>
"""


def _ref(**extra) -> WorkRef:
    return WorkRef(
        id="2833",
        source="onemorelibrary",
        extra={
            "title": "On the Comparative Place of Interest",
            "source_url": PAGE_URL,
            "category_id": "art-232",
            "category_name": "Art",
            "languages": ["en"],
            **extra,
        },
    )


def test_parse_book_page_extracts_metadata_and_download_links():
    work = parse_book_page(BOOK_PAGE, _ref(), PAGE_URL)

    assert work is not None
    assert work.id == "2833"
    assert work.title == "On the Comparative Place of Interest"
    assert work.languages == ["en"]
    assert work.license == "CC BY-SA 4.0"
    assert work.published == "1851"
    assert work.popularity == 1226 + 440 + 352
    assert work.source_url == PAGE_URL
    assert [book_format.name for book_format in work.formats] == ["epub", "pdf"]
    epub_url = work.formats[0].url
    assert epub_url is not None
    assert epub_url.endswith("fid=14599")
    assert work.formats[0].media_type == "application/epub+zip"
    assert work.extra["translator"] == "T. Bailey Saunders"
    assert work.extra["edition"] == "A. L. Burt Company"


def test_parse_book_page_maps_creator_and_collections():
    work = parse_book_page(BOOK_PAGE, _ref(), PAGE_URL)

    assert work is not None
    (creator,) = work.creators
    assert creator.id == "358"
    assert creator.name == "Arthur Schopenhauer"
    assert creator.sort_name == "Schopenhauer"
    assert creator.extra["wikipedia_url"].endswith("Arthur_Schopenhauer")
    assert [collection.name for collection in work.collections] == [
        "Art",
        "Schopenhauer Collection",
    ]
    assert work.collections[0].kind == "category"


def test_parse_book_page_uses_page_cover_and_falls_back_to_listing_category():
    work = parse_book_page(BOOK_PAGE, _ref(), PAGE_URL)

    assert work is not None
    assert work.cover is not None
    cover_url = work.cover.source_url
    assert cover_url is not None
    assert cover_url.endswith("2833_main.png")


def test_parse_book_page_returns_none_without_title():
    assert parse_book_page("<html><body><p>no book</p></body></html>", _ref()) is None


def test_fetch_reads_and_caches_pages(tmp_path):
    class Engine(DownloadEngine):
        def __init__(self):
            self.calls = 0

        def fetch_bytes(self, url, headers=None):
            del url, headers
            self.calls += 1
            return BOOK_PAGE.encode("utf-8")

    engine = Engine()
    metadata = OnemorelibraryMetadata(
        "https://onemorelibrary.com", engine=engine, cache_dir=tmp_path
    )

    first = list(metadata.fetch([_ref()]))
    second = list(metadata.fetch([_ref()]))

    assert [work.id for work in first] == [work.id for work in second] == ["2833"]
    assert engine.calls == 1
    assert (tmp_path / "onemorelibrary_metadata" / "2833.html").exists()
