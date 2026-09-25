"""Project Gutenberg-specific command-line options."""

from typing import Any

from papers2zim.core.utils import critical_error

SUPPORTED_LCC_SHELVES = {
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "J",
    "K",
    "L",
    "M",
    "N",
    "P",
    "PA",
    "PB",
    "PC",
    "PD",
    "PE",
    "PF",
    "PG",
    "PH",
    "PJ",
    "PK",
    "PL",
    "PM",
    "PN",
    "PQ",
    "PR",
    "PS",
    "PT",
    "PZ",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "Z",
}

CLI_OPTIONS = {
    "--lcc-shelves": (
        "  --lcc-shelves=<shelves>         Comma-separated LCC shelf codes to "
        "include (e.g., P,PR,Q). Use 'all' for every shelf"
    ),
}


def parse_options(arguments: dict[str, Any]) -> dict[str, Any]:
    lcc_shelves_arg = arguments.get("--lcc-shelves")
    if lcc_shelves_arg is None:
        return {}
    if lcc_shelves_arg.strip().lower() == "all":
        return {"collections": []}
    collections = [
        item.strip().upper() for item in lcc_shelves_arg.split(",") if item.strip()
    ]
    invalid = set(collections) - SUPPORTED_LCC_SHELVES
    if invalid:
        critical_error(f"Unsupported LCC shelf code(s): {', '.join(sorted(invalid))}")
    return {"collections": collections}


def handle_cli_action(_catalog: Any, _options: dict[str, Any]) -> bool:
    return False
