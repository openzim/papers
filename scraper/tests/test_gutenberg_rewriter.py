"""Tests for Gutenberg HTML asset reference rewriting.

Regression tests for #131: `handle_zipped_html` now preserves a book's
original subfolder layout (`images/`, `style/`, `music/`, ...) under the
book's own `{work.id}/` ZIM folder, so every local reference to a bundled
asset (not just `<img src>` to `images/`) must be rewritten to match.
"""

import pytest

from papers2zim.core.models import Work
from papers2zim.sources.gutenberg.rewriter import (
    transform_asset_path,
    update_html_for_static,
)


def _work(book_id="11") -> Work:
    return Work(id=book_id, source="gutenberg", title="A Book")


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("images/cover.jpg", "11/images/cover.jpg"),
        ("images/cover.jpg?v=2", "11/images/cover.jpg"),
        ("images/cover.jpg#frag", "11/images/cover.jpg"),
        ("images/foo%20bar.jpg", "11/images/foo bar.jpg"),
        ("style/arctic.css", "11/style/arctic.css"),
        ("music/11-1.mid", "11/music/11-1.mid"),
        ("cover.jpg", "11/cover.jpg"),
        ("", None),
        ("#top", None),
        ("/ebooks/11", None),
        ("https://www.gutenberg.org/ebooks/11", None),
        ("mailto:help@gutenberg.org", None),
    ],
)
def test_transform_asset_path(path, expected):
    assert transform_asset_path("11", path) == expected


def test_rewrites_img_src_in_non_images_subfolder():
    html = '<html><body><img id="plate" src="img/pl01.jpg"></body></html>'
    soup = update_html_for_static(_work(), html, [])
    img = soup.find(id="plate")
    assert img is not None
    assert img["src"] == "11/img/pl01.jpg.webp"


def test_rewrites_stylesheet_href():
    html = (
        '<html><head><link rel="stylesheet" href="style/arctic.css"></head>'
        "<body></body></html>"
    )
    soup = update_html_for_static(_work(), html, [])
    link = soup.find("link", rel="stylesheet")
    assert link is not None
    assert link["href"] == "11/style/arctic.css"


def test_rewrites_anchor_href_to_bundled_asset():
    html = '<html><body><a id="play" href="music/11-1.mid">Play</a></body></html>'
    soup = update_html_for_static(_work(), html, [])
    link = soup.find(id="play")
    assert link is not None
    assert link["href"] == "11/music/11-1.mid"


def test_leaves_external_and_anchor_links_untouched():
    html = (
        "<html><body>"
        '<a id="ext" href="https://www.gutenberg.org/ebooks/11">PG</a>'
        '<a id="anchor" href="#top">Top</a>'
        "</body></html>"
    )
    soup = update_html_for_static(_work(), html, [])
    ext_link = soup.find(id="ext")
    anchor_link = soup.find(id="anchor")
    assert ext_link is not None
    assert anchor_link is not None
    assert ext_link["href"] == "https://www.gutenberg.org/ebooks/11"
    assert anchor_link["href"] == "#top"


def test_rewrites_icon_cover_in_non_images_subfolder():
    html = (
        '<html><head><link rel="icon" href="shavings_files/title.gif"/></head>'
        "<body></body></html>"
    )
    work = _work()
    soup = update_html_for_static(work, html, [])
    assert work.extra["_cover_href"] == "shavings_files/title.gif"
    icon_link = soup.find("link", rel="icon")
    assert icon_link is not None
    assert icon_link["href"] == "11/shavings_files/title.gif"


def test_rewrites_every_icon_link_when_the_head_repeats_it():
    html = (
        "<html><head>"
        '<link href="images/cover_front.jpg" rel="icon" type="image/x-cover"'
        ' id="id-3721072283725311344"/>'
        '<link href="images/cover_front.jpg" rel="icon" type="image/x-cover"'
        ' id="id-1536236865570670334"/>'
        "</head><body></body></html>"
    )
    work = _work()
    soup = update_html_for_static(work, html, [])

    assert work.extra["_cover_href"] == "images/cover_front.jpg"
    assert [link["href"] for link in soup.find_all("link", rel="icon")] == [
        "11/images/cover_front.jpg.webp",
        "11/images/cover_front.jpg.webp",
    ]


def test_ignores_icon_links_that_are_not_local_assets():
    html = (
        "<html><head>"
        '<link rel="icon" href="images/cover.jpg" id="local-href"/>'
        '<link rel="icon" href="#anchor" id="anchor-href"/>'
        '<link rel="icon" id="no-href"/>'
        "</head><body></body></html>"
    )
    work = _work()
    soup = update_html_for_static(work, html, [])

    assert work.extra["_cover_href"] == "images/cover.jpg"
    icon_links = soup.find_all("link", rel="icon")
    assert [link.get("href") for link in icon_links] == [
        "11/images/cover.jpg.webp",
        "#anchor",
        None,
    ]
