from urllib.parse import quote

import pytest

from papers2zim.core.utils import (
    archive_name_for,
    article_name_for,
    book_name_for_fs,
    fname_for,
    normalize,
    slugify,
)


def test_book_name_for_fs(mock_work):
    assert book_name_for_fs(mock_work) == "Travels in the Great Desert of Sahara"


def test_book_name_for_fs_sanitizes_slashes(mock_work):
    mock_work.title = "Foo / Bar"
    assert book_name_for_fs(mock_work) == "Foo - Bar"


def test_book_name_for_fs_truncates_long_titles(mock_work):
    mock_work.title = "x" * 300
    assert len(book_name_for_fs(mock_work)) == 230


def test_article_name_for(mock_work):
    assert article_name_for(mock_work) == "Travels in the Great Desert of Sahara.22094"


def test_article_name_for_cover(mock_work):
    assert (
        article_name_for(mock_work, cover=True)
        == "Travels in the Great Desert of Sahara_cover.22094"
    )


def test_archive_name_for(mock_work):
    assert (
        archive_name_for(mock_work, "epub")
        == "Travels in the Great Desert of Sahara.22094.epub"
    )


def test_fname_for(mock_work):
    assert fname_for(mock_work, "html") == "22094.html"


def test_normalize_none():
    assert normalize(None) is None


def test_normalize_combines_characters():
    # "é" as e + combining acute should normalize to single codepoint
    assert normalize("é") == "é"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("Bleak House", "bleak-house", id="plain"),
        pytest.param("  Bleak - House  ", "bleak-house", id="trimmed"),
        pytest.param("Les Misérables", "les-misérables", id="accents"),
        pytest.param("Alice's Adventures", "alice-s-adventures", id="apostrophe"),
        pytest.param("Commune de Amiens/Nancy", "commune-de-amiens-nancy", id="slash"),
        pytest.param("Snow_White", "snow-white", id="underscore"),
        pytest.param("红楼梦", "红楼梦", id="cjk"),
        pytest.param("الأيام", "الأيام", id="arabic"),
        pytest.param("🎉🎉", "", id="emoji_only"),
        pytest.param("", "", id="empty"),
    ],
)
def test_slugify(text, expected):
    assert slugify(text) == expected


def test_slugify_budget_applies_to_percent_encoded_length():
    slug = slugify("汉" * 40, max_encoded_length=30)
    assert len(quote(slug)) <= 30
    assert slug == "汉" * 3


def test_slugify_budget_never_splits_a_character():
    assert slugify("ab汉", max_encoded_length=10) == "ab"


def test_slugify_strips_trailing_hyphen_after_truncation():
    assert slugify("a" * 5 + "-b" * 5, max_encoded_length=6) == "aaaaa"
