"""Tests for offline mirroring of explicitly declared OTL online editions."""

from base64 import b64decode
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import requests
from bs4 import BeautifulSoup
from PIL import Image

from papers2zim.core.models import Format, Work
from papers2zim.sources.opentextbooks.html_mirror import download_html_edition


class StubEngine:
    def __init__(self, pages: dict[str, bytes]):
        self.pages = pages
        self.fetched: list[str] = []

    def fetch_bytes(self, url: str) -> bytes:
        self.fetched.append(url)
        if url not in self.pages:
            raise requests.HTTPError(f"404 for {url}")
        return self.pages[url]


def _work() -> Work:
    return Work(id="10", source="opentextbooks", title="Calculus")


PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/"
    "9K3jKQAAAABJRU5ErkJggg=="
)
ROOT_URL = "https://books.example.edu/calculus/"
CHAPTER_URL = "https://books.example.edu/calculus/chapter.html"


def _mirror(chapter_body: bytes, **extra_pages: bytes) -> dict[str, bytes]:
    root = (
        b"<!doctype html><html><body>"
        + b"x" * 600
        + b'<a href="chapter.html">Chapter</a></body></html>'
    )
    chapter = b"<!doctype html><html><body>" + b"y" * 700 + chapter_body
    chapter += b"</body></html>"
    pages = {ROOT_URL: root, CHAPTER_URL: chapter}
    for name, content in extra_pages.items():
        pages[f"{ROOT_URL}{name}"] = content
    with TemporaryDirectory() as directory:
        edition = download_html_edition(
            StubEngine(pages), _work(), ROOT_URL, ["html"], directory=Path(directory)
        )
        assert edition is not None
        return {path: fpath.read_bytes() for path, fpath in edition.pages.items()}


def _chapter_html(pages: dict[str, bytes]) -> bytes:
    return next(
        content
        for path, content in pages.items()
        if path.startswith("html/10/") and "/assets/" not in path
    )


def test_mirrors_linked_chapters_and_rewrites_navigation(tmp_path):
    root_url = "https://books.example.edu/calculus/"
    chapter_url = "https://books.example.edu/calculus/chapter-1.html"
    root = (
        b"<!doctype html><html><body><h1>Contents</h1>"
        + b"x" * 600
        + b'<a href="chapter-1.html">Chapter 1</a></body></html>'
    )
    chapter = b"<!doctype html><html><body>" + b"y" * 700 + b"</body></html>"

    edition = download_html_edition(
        StubEngine({root_url: root, chapter_url: chapter}),
        _work(),
        root_url,
        ["html"],
        directory=tmp_path,
    )

    assert edition is not None
    companion_paths = set(edition.pages) - {"Calculus.10"}
    assert len(companion_paths) == 1
    (companion_path,) = companion_paths
    assert companion_path.startswith("html/10/")
    assert (
        f'href="{companion_path}"'.encode() in edition.pages["Calculus.10"].read_bytes()
    )
    companion_html = edition.pages[companion_path].read_bytes()
    assert b'href="../../css/html-reader-controls.css"' in companion_html
    assert b'src="../../js/html-reader-controls.js"' in companion_html
    assert b'src="../../icons/info.svg"' in companion_html


def test_rejects_a_landing_page_without_mirrored_book_pages(tmp_path):
    url = "https://books.example.edu/calculus/"
    page = b"<!doctype html><html><body>" + b"x" * 1000 + b"</body></html>"

    assert (
        download_html_edition(
            StubEngine({url: page}), _work(), url, ["html"], directory=tmp_path
        )
        is None
    )


def test_mirrors_and_rewrites_stylesheets_and_images(tmp_path):
    root_url = "https://books.example.edu/calculus/"
    chapter_url = "https://books.example.edu/calculus/chapter.html"
    css_url = "https://books.example.edu/calculus/theme.css"
    cover_url = "https://books.example.edu/calculus/images/cover.png"
    icon_url = "https://books.example.edu/calculus/images/icon.png"
    png = b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/"
        "9K3jKQAAAABJRU5ErkJggg=="
    )
    root = (
        b'<!doctype html><html><head><link rel="stylesheet" href="theme.css">'
        b"</head><body>"
        + b"x" * 600
        + b'<a href="chapter.html">Chapter</a><img src="images/cover.png">'
        + b"</body></html>"
    )
    chapter = b"<!doctype html><html><body>" + b"y" * 700 + b"</body></html>"
    edition = download_html_edition(
        StubEngine(
            {
                root_url: root,
                chapter_url: chapter,
                css_url: b"body { background: url('images/icon.png'); }",
                cover_url: png,
                icon_url: png,
            }
        ),
        _work(),
        root_url,
        ["html"],
        directory=tmp_path,
    )

    assert edition is not None
    asset_paths = [path for path in edition.pages if "/assets/" in path]
    assert len(asset_paths) == 3
    root_html = edition.pages["Calculus.10"].read_bytes()
    assert b'href="html/10/assets/' in root_html
    assert b'src="html/10/assets/' in root_html
    stylesheet_path = next(path for path in asset_paths if path.endswith(".css"))
    stylesheet = edition.pages[stylesheet_path].read_bytes()
    css_asset_name = stylesheet.split(b"url('", 1)[1].split(b"')", 1)[0].decode()
    assert f"html/10/assets/{css_asset_name}" in edition.pages
    assert b"html-reader-controls" in root_html
    assert b"scroll-to-top" in root_html


def test_adds_download_controls_for_available_binary_editions(tmp_path):
    root_url = "https://books.example.edu/calculus/"
    chapter_url = "https://books.example.edu/calculus/chapter.html"
    root = (
        b"<!doctype html><html><body>"
        + b"x" * 600
        + b'<a href="chapter.html">Chapter</a></body></html>'
    )
    chapter = b"<!doctype html><html><body>" + b"y" * 700 + b"</body></html>"
    work = _work()
    work.formats = [
        Format(
            name="PDF",
            media_type="application/pdf",
            url="https://books.example.edu/calculus.pdf",
        )
    ]

    edition = download_html_edition(
        StubEngine({root_url: root, chapter_url: chapter}),
        work,
        root_url,
        ["html", "pdf"],
        directory=tmp_path,
    )

    assert edition is not None
    assert b'href="Calculus.10.pdf"' in edition.pages["Calculus.10"].read_bytes()
    assert b"html-reader-btn-pdf" in edition.pages["Calculus.10"].read_bytes()


def test_mirrors_more_than_64_mib_without_truncating(tmp_path):
    root = (
        b"<!doctype html><html><body>"
        + b"x" * 600
        + b'<a href="chapter.html">Chapter</a></body></html>'
    )
    chapter = (
        b'<!doctype html><html><body><script src="first.js"></script>'
        b'<script src="second.js"></script></body></html>'
    )
    payload = b" " * (33 * 1024 * 1024)
    edition = download_html_edition(
        StubEngine(
            {
                ROOT_URL: root,
                CHAPTER_URL: chapter,
                ROOT_URL + "first.js": payload,
                ROOT_URL + "second.js": payload,
            }
        ),
        _work(),
        ROOT_URL,
        ["html"],
        directory=tmp_path,
    )

    assert edition is not None
    scripts = [fpath for path, fpath in edition.pages.items() if path.endswith(".js")]
    assert len(scripts) == 2
    assert all(fpath.stat().st_size == len(payload) for fpath in scripts)
    assert all(isinstance(fpath, Path) for fpath in edition.pages.values())
    assert all(fpath.parent == tmp_path for fpath in edition.pages.values())


def test_keeps_original_asset_path_when_webp_conversion_fails(monkeypatch, tmp_path):
    root_url = "https://books.example.edu/calculus/"
    chapter_url = "https://books.example.edu/calculus/chapter.html"
    image_url = "https://books.example.edu/calculus/cover.png"
    root = (
        b"<!doctype html><html><body>"
        + b"x" * 600
        + b'<a href="chapter.html">Chapter</a><img src="cover.png">'
        + b"</body></html>"
    )
    chapter = b"<!doctype html><html><body>" + b"y" * 700 + b"</body></html>"
    monkeypatch.setattr(
        "papers2zim.sources.opentextbooks.html_mirror.ImageProcessor.optimize_image_content",
        lambda _content: (_ for _ in ()).throw(ValueError("invalid image")),
    )

    edition = download_html_edition(
        StubEngine({root_url: root, chapter_url: chapter, image_url: b"not an image"}),
        _work(),
        root_url,
        ["html"],
        directory=tmp_path,
    )

    assert edition is not None
    assert b'.png"' in edition.pages["Calculus.10"].read_bytes()
    assert b".webp" not in edition.pages["Calculus.10"].read_bytes()


def test_mirrors_scripts_and_rewrites_them_relative_to_each_page():
    pages = _mirror(
        b'<script src="shared/book.js"></script>',
        **{"shared/book.js": b"function replaceIframe() {}"},
    )

    (script_path,) = [path for path in pages if path.endswith(".js")]
    assert pages[script_path] == b"function replaceIframe() {}"
    script_name = script_path.removeprefix("html/10/")
    assert f'src="{script_name}"'.encode() in _chapter_html(pages)


def test_points_links_to_pages_left_out_of_the_zim_back_to_the_source():
    chapter = _chapter_html(
        _mirror(
            b'<a href="missing.html">Gone</a>'
            b'<a href="larson-ch01#larson-ch01">Chapter 1</a>'
            b'<a href="/coulston">Author</a>'
            b'<a href="#section-2">Below</a>'
        )
    )

    assert b'href="https://books.example.edu/calculus/missing.html"' in chapter
    assert (
        b'href="https://books.example.edu/calculus/larson-ch01#larson-ch01"' in chapter
    )
    assert b'href="https://books.example.edu/coulston"' in chapter
    assert b'href="#section-2"' in chapter


def test_drops_images_and_scripts_that_could_not_be_stored_offline():
    chapter = _chapter_html(
        _mirror(
            b'<img src="figures/missing.png" alt="lost">'
            b'<script src="https://cdn.mathjax.org/mathjax/latest/MathJax.js'
            b'?config=MML_HTMLorMML"></script>'
            b'<img src="data:image/png;base64,AAAA" alt="inline">'
        )
    )

    assert b"missing.png" not in chapter
    assert b"mathjax" not in chapter
    assert b'src="data:image/png;base64,AAAA"' in chapter


def test_mirrors_images_hosted_outside_the_edition(tmp_path):
    image_url = "https://upload.wikimedia.org/commons/figure.png"
    root = (
        b"<!doctype html><html><body>"
        + b"x" * 600
        + b'<a href="chapter.html">Chapter</a>'
        + f'<img src="{image_url}"></body></html>'.encode()
    )
    chapter = b"<!doctype html><html><body>" + b"y" * 700 + b"</body></html>"

    edition = download_html_edition(
        StubEngine({ROOT_URL: root, CHAPTER_URL: chapter, image_url: PNG}),
        _work(),
        ROOT_URL,
        ["html"],
        directory=tmp_path,
    )

    assert edition is not None
    assert image_url.encode() not in edition.pages["Calculus.10"].read_bytes()
    assert b'src="html/10/assets/' in edition.pages["Calculus.10"].read_bytes()


def test_replaces_online_only_embeds_with_links_to_them():
    chapter = _chapter_html(
        _mirror(
            b'<iframe src="https://www.youtube.com/embed/abc"></iframe>'
            b'<a data-iframe-code=\'&lt;iframe src="http://www.youtube.com/v/xyz"'
            b'&gt;&lt;/iframe&gt;\' href="http://www.youtube.com/v/xyz"'
            b' onclick="return replaceIframe(this)">(click to see video)</a>'
        )
    )

    assert b"<iframe" not in chapter
    assert b'<a href="https://www.youtube.com/embed/abc">' in chapter
    assert b"data-iframe-code" not in chapter
    assert b"onclick" not in chapter
    assert b'href="http://www.youtube.com/v/xyz"' in chapter


def test_mirrors_more_than_300_pages_and_500_assets(tmp_path):
    pages = {
        ROOT_URL: b"<!doctype html><html><body>"
        + b"x" * 600
        + b"".join(
            f'<a href="chapter-{i}.html">Chapter {i}</a>'.encode() for i in range(301)
        )
        + b"</body></html>"
    }
    chapter = (
        b'<!doctype html><html><head><link rel="stylesheet" href="theme.css">'
        b'</head><body><a href="./#toc">Contents</a>'
        b'<a href="chapter-300.html#end">Last chapter</a>'
        + b"".join(f'<script src="lib-{i}.js"></script>'.encode() for i in range(501))
        + b"</body></html>"
    )
    pages.update({ROOT_URL + f"chapter-{i}.html": chapter for i in range(301)})
    pages.update({ROOT_URL + f"lib-{i}.js": b"var x;" for i in range(501)})
    pages[ROOT_URL + "theme.css"] = b"body { background: url(last.png); }"
    image_data = BytesIO()
    Image.new("RGB", (2, 2), "red").save(image_data, format="PNG")
    pages[ROOT_URL + "last.png"] = image_data.getvalue()
    engine = StubEngine(pages)
    edition = download_html_edition(
        engine, _work(), ROOT_URL, ["html"], directory=tmp_path
    )

    assert edition is not None
    assert len(edition.pages) == 302 + 503
    assert len(engine.fetched) == len(set(engine.fetched)) == len(pages)
    assert sum(path.endswith(".html") for path in edition.pages) == 301
    assert sum(path.endswith(".js") for path in edition.pages) == 501
    root = BeautifulSoup(edition.pages["Calculus.10"].read_bytes(), "html.parser")
    last_link = root.find("a", string="Chapter 300")
    assert last_link is not None
    assert last_link["href"] in edition.pages
    css = next(
        fpath.read_bytes()
        for path, fpath in edition.pages.items()
        if path.endswith(".css")
    )
    image = css.split(b"url(", 1)[1].split(b")", 1)[0].decode()
    assert image.endswith(".webp")
    assert f"html/10/assets/{image}" in edition.pages


def test_keeps_page_crawl_inside_the_edition_and_deduplicates_fragments(tmp_path):
    root = (
        b"<!doctype html><html><body>"
        + b"x" * 600
        + b'<a href="chapter.html">Chapter</a>'
        b'<a href="chapter.html#section">Same chapter</a>'
        b'<a href="../other.html">Another book</a>'
        b'<a href="https://elsewhere.example/chapter.html">External</a>'
        b'<a href="/calculus-other/chapter.html">Sibling</a></body></html>'
    )
    engine = StubEngine(
        {
            ROOT_URL: root,
            CHAPTER_URL: b'<html><body><a href="./">Contents</a></body></html>',
        }
    )
    edition = download_html_edition(
        engine, _work(), ROOT_URL, ["html"], directory=tmp_path
    )

    assert edition is not None
    assert engine.fetched == [ROOT_URL, CHAPTER_URL]
    html = edition.pages["Calculus.10"].read_bytes()
    assert b'href="https://books.example.edu/other.html"' in html


def test_propagates_disk_write_failure_instead_of_returning_a_partial_edition(
    tmp_path, monkeypatch
):
    root = b"<!doctype html><html><body>" + b"x" * 600 + b"</body></html>"

    def fail_write(_self, _content):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    with pytest.raises(OSError, match="disk full"):
        download_html_edition(
            StubEngine({ROOT_URL: root}),
            _work(),
            ROOT_URL,
            ["html"],
            directory=tmp_path,
        )
