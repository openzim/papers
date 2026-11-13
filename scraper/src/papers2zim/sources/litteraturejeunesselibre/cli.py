"""Littérature jeunesse libre-specific command-line options.

An LJL scrape selects at most one filter family from the OPDS catalogue: a set of
series, authors, categories or title prefixes. These filters are mutually
exclusive because the catalogue exposes one feed per filter. Categories are the
broad collections derived from LJL tags, not the raw tags themselves. The
available filter values can be listed with the ``--list-ljl-*`` options, and
specific books can be selected by UUID with ``--ljl-ids``.
"""

import sys
from typing import Any

from papers2zim.core.opds import parse_uuid
from papers2zim.core.utils import critical_error

CLI_OPTIONS = {
    "--ljl-series": (
        "  --ljl-series=<series>          Comma-separated LJL series names"
    ),
    "--ljl-authors": (
        "  --ljl-authors=<authors>        Comma-separated LJL author names"
    ),
    "--ljl-categories": (
        "  --ljl-categories=<categories>  Comma-separated LJL category names"
    ),
    "--ljl-titles": (
        "  --ljl-titles=<titles>          Comma-separated LJL title prefixes "
        "(letters or numbers)"
    ),
    "--ljl-ids": ("  --ljl-ids=<ids>                Comma-separated LJL book UUIDs"),
    "--list-ljl-series": ("  --list-ljl-series               List LJL series and exit"),
    "--list-ljl-authors": (
        "  --list-ljl-authors              List LJL authors and exit"
    ),
    "--list-ljl-categories": (
        "  --list-ljl-categories           List LJL categories and exit"
    ),
    "--list-ljl-titles": (
        "  --list-ljl-titles               List LJL title prefixes and exit"
    ),
}


def _split_csv(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def parse_options(arguments: dict[str, Any]) -> dict[str, Any]:
    if arguments.get("--books"):
        critical_error(
            "Littérature jeunesse libre does not support --books; select books "
            "with one of --ljl-series, --ljl-authors, --ljl-categories or "
            "--ljl-titles"
        )

    series = _split_csv(arguments.get("--ljl-series"))
    authors = _split_csv(arguments.get("--ljl-authors"))
    categories = _split_csv(arguments.get("--ljl-categories"))
    titles = _split_csv(arguments.get("--ljl-titles"))
    book_ids = []
    for value in _split_csv(arguments.get("--ljl-ids")):
        uuid = parse_uuid(value)
        if uuid is None:
            critical_error(
                f"Comma-separated --ljl-ids values must be full UUIDs, got {value!r}"
            )
        book_ids.append(uuid)
    if sum(map(bool, (series, authors, categories, titles))) > 1:
        critical_error(
            "Use only one Littérature jeunesse libre filter at a time: "
            "--ljl-series, --ljl-authors, --ljl-categories or --ljl-titles"
        )

    return {
        "series": series,
        "authors": authors,
        "categories": categories,
        "title": titles,
        "book_ids": book_ids,
        "list_series": bool(arguments.get("--list-ljl-series")),
        "list_authors": bool(arguments.get("--list-ljl-authors")),
        "list_categories": bool(arguments.get("--list-ljl-categories")),
        "list_titles": bool(arguments.get("--list-ljl-titles")),
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
