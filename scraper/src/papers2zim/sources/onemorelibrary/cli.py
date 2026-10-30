"""One More Library-specific command-line options."""

import sys
from typing import Any

from papers2zim.core.utils import critical_error

CLI_OPTIONS = {
    "--categories": (
        "  --categories=<categories>       Comma-separated One More Library "
        "categories (names or slugs)"
    ),
    "--oml-ids": ("  --oml-ids=<ids>                 Exact One More Library book IDs"),
    "--list-categories": (
        "  --list-categories               List One More Library categories and exit"
    ),
    "--refresh-oml-catalog": (
        "  --refresh-oml-catalog           Refresh the One More Library catalog and "
        "exit"
    ),
}


def parse_options(arguments: dict[str, Any]) -> dict[str, Any]:
    categories = [
        item.strip()
        for item in (arguments.get("--categories") or "").split(",")
        if item.strip()
    ]
    book_ids = [
        item.strip()
        for item in (arguments.get("--oml-ids") or "").split(",")
        if item.strip()
    ]
    if any(not book_id.isdigit() for book_id in book_ids):
        critical_error(
            "--oml-ids must be a comma-separated list of numeric One More Library "
            "book IDs"
        )
    if book_ids and arguments.get("--books"):
        critical_error("Use either --books or --oml-ids, not both")
    return {
        "collections": categories,
        "book_ids": book_ids,
        "list_categories": bool(arguments.get("--list-categories")),
        "refresh_catalog": bool(arguments.get("--refresh-oml-catalog")),
    }


def handle_cli_action(catalog: Any, options: dict[str, Any]) -> bool:
    if options["refresh_catalog"]:
        catalog.refresh()
        return True
    if options["list_categories"]:
        for name, category_id in catalog.list_categories():
            sys.stdout.write(f"{name}\t{category_id}\n")
        return True
    return False
