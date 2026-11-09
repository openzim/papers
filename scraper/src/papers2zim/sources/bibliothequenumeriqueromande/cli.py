"""Bibliothèque numérique romande-specific command-line options.

A BNR scrape selects at most one filter family from the OPDS catalogue: a set of
series, authors, categories (tags) or title prefixes. These filters are mutually
exclusive because the catalogue exposes one feed per filter. Without any filter,
every title page is fetched, which yields the whole catalogue. The available
filter values can be listed with the ``--list-bnr-*`` options, and specific
books can be selected by UUID with ``--bnr-ids``.
"""

import sys
from typing import Any

from papers2zim.core.utils import critical_error
from papers2zim.sources.bibliothequenumeriqueromande.catalog import parse_uuid

CLI_OPTIONS = {
    "--bnr-series": (
        "  --bnr-series=<series>          Comma-separated BNR series names"
    ),
    "--bnr-authors": (
        "  --bnr-authors=<authors>        Comma-separated BNR author names"
    ),
    "--bnr-categories": (
        "  --bnr-categories=<categories>  Comma-separated BNR category names"
    ),
    "--bnr-titles": (
        "  --bnr-titles=<titles>          Comma-separated BNR title prefixes "
        "(letters or numbers)"
    ),
    "--bnr-ids": ("  --bnr-ids=<ids>                Comma-separated BNR book UUIDs"),
    "--list-bnr-series": ("  --list-bnr-series               List BNR series and exit"),
    "--list-bnr-authors": (
        "  --list-bnr-authors              List BNR authors and exit"
    ),
    "--list-bnr-categories": (
        "  --list-bnr-categories           List BNR categories and exit"
    ),
    "--list-bnr-titles": (
        "  --list-bnr-titles               List BNR title prefixes and exit"
    ),
}


def _split_csv(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def parse_options(arguments: dict[str, Any]) -> dict[str, Any]:
    if arguments.get("--books"):
        critical_error(
            "Bibliothèque numérique romande does not support --books; select books "
            "with one of --bnr-series, --bnr-authors, --bnr-categories or "
            "--bnr-titles"
        )

    series = _split_csv(arguments.get("--bnr-series"))
    authors = _split_csv(arguments.get("--bnr-authors"))
    categories = _split_csv(arguments.get("--bnr-categories"))
    titles = _split_csv(arguments.get("--bnr-titles"))
    book_ids = []
    for value in _split_csv(arguments.get("--bnr-ids")):
        uuid = parse_uuid(value)
        if uuid is None:
            critical_error(
                f"Comma-separated --bnr-ids values must be full UUIDs, got {value!r}"
            )
        book_ids.append(uuid)
    if sum(map(bool, (series, authors, categories, titles))) > 1:
        critical_error(
            "Use only one Bibliothèque numérique romande filter at a time: "
            "--bnr-series, --bnr-authors, --bnr-categories or --bnr-titles"
        )

    return {
        "series": series,
        "authors": authors,
        "categories": categories,
        "title": titles,
        "book_ids": book_ids,
        "list_series": bool(arguments.get("--list-bnr-series")),
        "list_authors": bool(arguments.get("--list-bnr-authors")),
        "list_categories": bool(arguments.get("--list-bnr-categories")),
        "list_titles": bool(arguments.get("--list-bnr-titles")),
    }


def handle_cli_action(catalog: Any, options: dict[str, Any]) -> bool:
    if options.get("list_series"):
        for name in catalog.list_series():
            sys.stdout.write(f"{name}\n")
        return True
    if options.get("list_authors"):
        for name in catalog.list_authors():
            sys.stdout.write(f"{name}\n")
        return True
    if options.get("list_categories"):
        for name in catalog.list_categories():
            sys.stdout.write(f"{name}\n")
        return True
    if options.get("list_titles"):
        for name in catalog.list_titles():
            sys.stdout.write(f"{name}\n")
        return True
    return False
