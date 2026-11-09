"""Tests for Bibliothèque numérique romande CLI option parsing."""

import pytest

from papers2zim.core.utils import CriticalError
from papers2zim.sources.bibliothequenumeriqueromande.cli import parse_options


def _empty_options() -> dict:
    return {
        "series": [],
        "authors": [],
        "categories": [],
        "title": [],
        "book_ids": [],
        "list_series": False,
        "list_authors": False,
        "list_categories": False,
        "list_titles": False,
    }


def test_no_filter_means_the_whole_catalogue():
    assert parse_options({}) == _empty_options()


def test_titles_are_split_and_stripped():
    options = parse_options({"--bnr-titles": " A , B "})

    assert options["title"] == ["A", "B"]
    assert options["series"] == []


def test_list_action_is_reported():
    options = parse_options({"--list-bnr-authors": True})

    assert options["list_authors"] is True
    assert options["list_series"] is False


def test_rejects_more_than_one_filter_family():
    with pytest.raises(CriticalError):
        parse_options({"--bnr-series": "A", "--bnr-authors": "B"})


def test_rejects_books_positions():
    with pytest.raises(CriticalError):
        parse_options({"--books": "1"})


def test_ids_accept_full_uuids_case_insensitively():
    options = parse_options(
        {
            "--bnr-ids": (
                " 87A3391F-6BF8-1014-9269-99B4F1E6D0DC , "
                "93A150D8-630A-4B26-B495-2E848BB09B9E "
            )
        }
    )

    assert options["book_ids"] == [
        "87a3391f-6bf8-1014-9269-99b4f1e6d0dc",
        "93a150d8-630a-4b26-b495-2e848bb09b9e",
    ]


def test_ids_reject_non_uuid_values():
    for value in ("other", "urn:uuid:87A3391F-6BF8-1014-9269-99B4F1E6D0DC"):
        with pytest.raises(CriticalError):
            parse_options({"--bnr-ids": value})
