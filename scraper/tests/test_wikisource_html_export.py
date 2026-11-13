"""Tests for turning ws-export HTML archives into ZIM pages."""

from io import BytesIO
from zipfile import ZIP_STORED, ZipFile

from papers2zim.core.models import Format, Work
from papers2zim.core.utils import article_name_for
from papers2zim.sources.wikisource.html_export import extract_html_edition

PNG = b"\x89PNG\r\n\x1a\n" + b"png bytes"
JPEG = b"\xff\xd8\xff" + b"jpeg bytes"


def _work() -> Work:
    return Work(
        id="en_first-book-12345678",
        source="wikisource",
        title="First Book",
        formats=[
            Format(
                name="epub",
                media_type="application/epub+zip",
                url="https://ws-export.wmcloud.org/?lang=en&format=epub&page=First_Book",
            ),
        ],
    )


def _archive(members: dict[str, bytes]) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_STORED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return output.getvalue()


def _html_archive() -> bytes:
    return _archive(
        {
            "index.html": (
                b'<html><head><link href="style.css" rel="stylesheet"/>'
                b"<title>First Book</title></head><body>"
                b'<img src="images/pic.png"/>'
                b'<a href="chapter two.html">Chapter</a>'
                b'<a href="https://en.wikisource.org/wiki/Author:A_Writer">Author</a>'
                b"</body></html>"
            ),
            "chapter two.html": (
                b'<html><body><a href="index.html">Back</a></body></html>'
            ),
            "style.css": b"body { background: url(images/bg.jpg); }",
            "images/pic.png": PNG,
            "images/bg.jpg": JPEG,
        }
    )


def test_extract_stores_pages_and_rewrites_references():
    work = _work()

    edition = extract_html_edition(_html_archive(), work, ["epub"])

    assert edition is not None
    root_path = article_name_for(work)
    assert edition.index_path == root_path
    assert set(edition.pages) == {
        root_path,
        f"html/{work.id}/chapter two.html",
        f"html/{work.id}/style.css",
        f"html/{work.id}/images/pic.png",
        f"html/{work.id}/images/bg.jpg",
    }

    root = edition.pages[root_path][0].decode()
    assert f'href="html/{work.id}/style.css"' in root
    assert f'src="html/{work.id}/images/pic.png"' in root
    assert f'href="html/{work.id}/chapter%20two.html"' in root
    assert 'href="https://en.wikisource.org/wiki/Author:A_Writer"' in root
    assert 'id="html-reader-controls"' in root
    assert edition.pages[f"html/{work.id}/style.css"][0] == (
        b"body { background: url(images/bg.jpg); }"
    )
    assert edition.pages[f"html/{work.id}/images/pic.png"] == (PNG, "image/png")
    assert edition.pages[f"html/{work.id}/images/bg.jpg"] == (JPEG, "image/jpeg")


def test_extract_links_reader_controls_to_the_requested_formats():
    work = _work()

    edition = extract_html_edition(_html_archive(), work, ["epub"])

    assert edition is not None
    root = edition.pages[edition.index_path][0].decode()
    assert "html-reader-btn-epub" in root
    assert f'href="First%20Book.{work.id}.epub"' in root


def test_extract_rejects_parent_traversing_members():
    work = _work()
    archive = _archive(
        {
            "index.html": b"<html><body>Hello</body></html>",
            "../evil.html": b"<html><body>evil</body></html>",
        }
    )

    edition = extract_html_edition(archive, work, [])

    assert edition is not None
    assert all(".." not in path for path in edition.pages)
    assert all("evil" not in path for path in edition.pages)


def test_extract_returns_none_without_an_html_page():
    edition = extract_html_edition(_archive({"style.css": b"body {}"}), _work(), [])

    assert edition is None


def test_extract_returns_none_for_a_non_zip_response():
    assert extract_html_edition(b"<!DOCTYPE html><html></html>", _work(), []) is None
