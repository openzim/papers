"""Tests for core.exporters.search_items_exporter."""

from unittest.mock import MagicMock

from papers2zim.core.exporters.search_items_exporter import export_book_search_item
from papers2zim.core.models import Creator, Work


def _work() -> Work:
    return Work(
        id="1342",
        source="gutenberg",
        title="Pride and Prejudice",
        creators=[Creator(id="68", display_name="Jane Austen")],
    )


def test_book_search_item_indexes_the_book_text_but_does_not_store_it():
    assembler = MagicMock()
    export_book_search_item(
        _work(), "It is a truth universally acknowledged.", assembler
    )

    kwargs = assembler.add_item_for.call_args.kwargs
    assert kwargs["path"] == "index/book_1342"
    assert kwargs["title"] == "Pride and Prejudice"
    index_data = kwargs["index_data"]
    assert index_data.get_title() == "Pride and Prejudice"
    assert "Jane Austen" in index_data.get_content()
    assert "It is a truth universally acknowledged." in index_data.get_content()
    # the redirect page itself only carries the short description
    assert "Jane Austen" in kwargs["content"]
    assert "universally" not in kwargs["content"]
    assert "index.html#/book/1342" in kwargs["content"]


def test_book_search_item_without_text_indexes_the_description_only():
    assembler = MagicMock()
    export_book_search_item(_work(), "", assembler)

    index_data = assembler.add_item_for.call_args.kwargs["index_data"]
    assert index_data.get_content() == "A book by Jane Austen."
