"""Wikisource-specific command-line options.

Language selection uses the shared ``--languages`` option (Wikisource is
organised per language). ``--wikisource-pages`` selects books by page name,
which, unlike ``--books`` positions, stays stable as the feed changes.
"""

from typing import Any

from papers2zim.core.utils import critical_error
from papers2zim.sources.wikisource.catalog import page_key

CLI_OPTIONS = {
    "--wikisource-pages": (
        "  --wikisource-pages=<pages>     Wikisource page names, as in the page URL"
    ),
}


def parse_options(arguments: dict[str, Any]) -> dict[str, Any]:
    # Split before decoding so a comma inside a page name can be passed as %2C.
    pages = [
        page_key(item)
        for item in (arguments.get("--wikisource-pages") or "").split(",")
        if item.strip()
    ]
    if pages and arguments.get("--books"):
        critical_error("Use either --books or --wikisource-pages, not both")
    return {"pages": pages}


def handle_cli_action(_catalog: Any, _options: dict[str, Any]) -> bool:
    return False
