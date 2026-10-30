from papers2zim.core.utils import (
    archive_name_for,
    article_name_for,
    author_sort_key,
    book_name_for_fs,
    fname_for,
    normalize,
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


def test_author_sort_key_orders_by_last_then_first_then_suffix():
    assert author_sort_key("Clarke", "Alice") < author_sort_key("Clarke", "Bob")
    assert author_sort_key("Andrews", "Henry Cranke") < author_sort_key("Smith")


def test_author_sort_key_disambiguates_same_last_and_first_name_by_suffix():
    assert author_sort_key("Smith", "John", "1850-1900") < author_sort_key(
        "Smith", "John", "1950-2000"
    )


def test_author_sort_key_drops_missing_parts():
    assert author_sort_key("Bob") == "Bob"
    assert author_sort_key(None, "Bob") == "Bob"
    assert author_sort_key(None, None, None) is None
    assert author_sort_key(None) is None


def test_normalize_none():
    assert normalize(None) is None


def test_normalize_combines_characters():
    # "é" as e + combining acute should normalize to single codepoint
    assert normalize("é") == "é"
