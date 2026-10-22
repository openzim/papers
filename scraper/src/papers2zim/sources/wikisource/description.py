"""Wikisource book descriptions, sourced from Wikidata.

The ws-export OPDS feed carries no description for its books, so a work's short
description is read from its Wikidata item. The Wikisource page named in the
feed is the ``<lang>wikisource`` sitelink that points at that item, and the
description is requested in the work's own language.

The lookup is best-effort and batched: page names are sent to Wikidata fifty at
a time through ``wbgetentities``. A work with no Wikidata item, or no
description in its language, is left without one rather than failing the build.
"""

import json
import urllib.parse

import requests

from papers2zim.constants import logger
from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.models import Work
from papers2zim.core.work_store import WorkStore

WIKIDATA_API = "https://www.wikidata.org/w/api.php"

# wbgetentities accepts at most 50 titles per request.
WIKIDATA_BATCH_SIZE = 50

# `Work.extra` key holding the ws-export page name (see wikisource.metadata).
PAGE_EXTRA_KEY = "wikisource_page"


def sitelink_site(lang: str) -> str:
    """Return the Wikidata sitelink site id for a Wikisource language code."""
    return f"{lang}wikisource"


def page_name(work: Work) -> str | None:
    """Return the Wikisource page name of `work`, or None when it has none."""
    page = work.extra.get(PAGE_EXTRA_KEY)
    if not isinstance(page, str) or not page:
        return None
    return urllib.parse.unquote(page).replace("_", " ").strip()


def work_language(work: Work) -> str | None:
    """Return the Wikisource language code of `work`, or None when unknown."""
    return work.languages[0] if work.languages else None


def normalized(title: str) -> str:
    """Return a whitespace- and case-insensitive key to match page names."""
    return " ".join(title.split()).casefold()


def parse_descriptions(payload: bytes, site: str, lang: str) -> dict[str, str]:
    """Map normalized page names to descriptions from a wbgetentities reply."""
    try:
        data = json.loads(payload)
    except ValueError:
        logger.warning(f"Invalid JSON in Wikidata response for {site}")
        return {}
    entities = data.get("entities")
    if not isinstance(entities, dict):
        return {}
    descriptions: dict[str, str] = {}
    for entity in entities.values():
        description = (entity.get("descriptions") or {}).get(lang)
        sitelink = (entity.get("sitelinks") or {}).get(site)
        if not isinstance(description, dict) or not isinstance(sitelink, dict):
            continue
        value = description.get("value")
        title = sitelink.get("title")
        if isinstance(value, str) and value and isinstance(title, str):
            descriptions[normalized(title)] = value
    return descriptions


def fetch_descriptions(
    engine: DownloadEngine, lang: str, titles: list[str]
) -> dict[str, str]:
    """Return {normalized page name: description} for up to 50 page names."""
    site = sitelink_site(lang)
    query = urllib.parse.urlencode(
        {
            "action": "wbgetentities",
            "format": "json",
            "props": "descriptions|sitelinks",
            "sitefilter": site,
            "languages": lang,
            "sites": site,
            "titles": "|".join(titles),
        }
    )
    try:
        payload = engine.fetch_bytes(f"{WIKIDATA_API}?{query}")
    except requests.RequestException as exc:
        logger.warning(f"Failed to fetch Wikidata descriptions for {site}: {exc}")
        return {}
    return parse_descriptions(payload, site, lang)


def enrich_work_descriptions(store: WorkStore, engine: DownloadEngine) -> None:
    """Fill in missing work descriptions from Wikidata, best-effort."""
    grouped: dict[str, list[tuple[str, Work]]] = {}
    for work in store.works:
        if work.description:
            continue
        lang = work_language(work)
        page = page_name(work)
        if lang and page:
            grouped.setdefault(lang, []).append((page, work))
    total = sum(len(entries) for entries in grouped.values())
    if not total:
        return

    logger.info(f"Looking up Wikidata descriptions for {total} Wikisource work(s)")
    enriched = 0
    for lang, entries in grouped.items():
        for start in range(0, len(entries), WIKIDATA_BATCH_SIZE):
            batch = entries[start : start + WIKIDATA_BATCH_SIZE]
            descriptions = fetch_descriptions(
                engine, lang, [page for page, _work in batch]
            )
            for page, work in batch:
                if description := descriptions.get(normalized(page)):
                    work.description = description
                    enriched += 1
    logger.info(f"Added Wikidata descriptions to {enriched} Wikisource work(s)")
