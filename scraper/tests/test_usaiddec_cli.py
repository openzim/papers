"""Tests for USAID DEC Archive-specific CLI option parsing."""

from unittest.mock import MagicMock

import pytest

from papers2zim.core.utils import CriticalError
from papers2zim.sources.usaiddec.cli import handle_cli_action, parse_options


def test_without_options_no_ids_are_requested_and_no_refresh():
    assert parse_options({}) == {"book_ids": [], "refresh_catalog": False}


def test_usaid_ids_are_trimmed_and_blank_entries_dropped():
    assert parse_options({"--usaid-ids": " PA000001 , ,PA000002,"}) == {
        "book_ids": ["PA000001", "PA000002"],
        "refresh_catalog": False,
    }


def test_refresh_flag_is_reported_as_an_option():
    assert parse_options({"--refresh-usaid-catalog": True}) == {
        "book_ids": [],
        "refresh_catalog": True,
    }


def test_usaid_ids_and_books_cannot_be_combined():
    with pytest.raises(CriticalError):
        parse_options({"--usaid-ids": "PA000001", "--books": "1"})


def test_refresh_option_refreshes_the_catalog_and_ends_the_run():
    catalog = MagicMock()

    assert handle_cli_action(catalog, {"refresh_catalog": True}) is True

    catalog.refresh.assert_called_once_with()


def test_without_refresh_the_catalog_is_left_alone():
    catalog = MagicMock()

    assert handle_cli_action(catalog, {"refresh_catalog": False}) is False

    catalog.refresh.assert_not_called()
