"""Wikisource-specific command-line options.

Language selection uses the shared ``--languages`` option (Wikisource is
organised per language). ``--wikisource-pages`` selects books by page name,
which, unlike ``--books`` positions, stays stable as the feed changes.
``--wikisource-feed`` names the ws-export OPDS feed to read when a language
directory advertises more than one, since the feed names are localized and the
scraper refuses to guess between them. Where a language advertises one feed it
is read regardless: feed names are per language.
"""

from typing import Any

from papers2zim.core.utils import critical_error
from papers2zim.sources.wikisource.catalog import page_key

CLI_OPTIONS = {
    "--wikisource-pages": (
        "  --wikisource-pages=<pages>     Wikisource page names, as in the page URL"
    ),
    "--wikisource-feed": (
        "  --wikisource-feed=<feed>       OPDS feed to use when a language "
        "has several"
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
    feed = (arguments.get("--wikisource-feed") or "").strip() or None
    return {"pages": pages, "feed": feed}


def handle_cli_action(_catalog: Any, _options: dict[str, Any]) -> bool:
    return False
