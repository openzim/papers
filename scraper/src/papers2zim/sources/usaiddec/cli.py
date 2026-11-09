"""USAID DEC Archive-specific command-line options."""

from typing import Any

from papers2zim.core.utils import critical_error

CLI_OPTIONS = {
    "--usaid-ids": (
        "  --usaid-ids=<ids>              Exact USAID DEC report IDs "
        "(Formatted Document IDs, comma-separated)"
    ),
    "--refresh-usaid-catalog": (
        "  --refresh-usaid-catalog        Refresh the USAID DEC dataset catalog and "
        "exit"
    ),
}


def parse_options(arguments: dict[str, Any]) -> dict[str, Any]:
    book_ids = [
        item.strip()
        for item in (arguments.get("--usaid-ids") or "").split(",")
        if item.strip()
    ]
    if book_ids and arguments.get("--books"):
        critical_error("Use either --books or --usaid-ids, not both")
    return {
        "book_ids": book_ids,
        "refresh_catalog": bool(arguments.get("--refresh-usaid-catalog")),
    }


def handle_cli_action(catalog: Any, options: dict[str, Any]) -> bool:
    if options.get("refresh_catalog"):
        catalog.refresh()
        return True
    return False
