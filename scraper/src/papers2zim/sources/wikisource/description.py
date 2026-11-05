"""Wikisource book descriptions, sourced from Wikidata.

The ws-export OPDS feed carries no description for its books, so a work's short
description is read from its Wikidata item. The Wikisource page named in the
feed is the ``<lang>wikisource`` sitelink that points at that item, and the
description is requested in the wiki's own language.

The lookup is best-effort and batched: page names are sent to Wikidata through
``wbgetentities`` in batches sized by their encoded URL length, so long
non-Latin titles do not overflow the request URL. A work with no Wikidata item,
or no description in its language, is left without one rather than failing the
build.
"""

import json
import urllib.parse

import requests

from papers2zim.constants import logger
from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.models import Work
from papers2zim.core.work_store import WorkStore
from papers2zim.sources.wikisource.catalog import page_key

WIKIDATA_API = "https://www.wikidata.org/w/api.php"

WIKIDATA_MAX_TITLES = 50
WIKIDATA_MAX_QUERY_BYTES = 6000

PAGE_EXTRA_KEY = "wikisource_page"
LANG_EXTRA_KEY = "wikisource_lang"


def sitelink_site(lang: str) -> str:
    """Return the Wikidata sitelink site id for a Wikisource language code."""
    return f"{lang}wikisource"


def title_key(title: str) -> str:
    """Return the MediaWiki title form used to match pages: spaces, first letter up."""
    key = page_key(title).replace("_", " ")
    return key[:1].upper() + key[1:]


def page_name(work: Work) -> str | None:
    """Return the Wikisource page name of `work`, or None when it has none."""
    page = work.extra.get(PAGE_EXTRA_KEY)
    if not isinstance(page, str) or not page:
        return None
    return page_key(page).replace("_", " ")


def work_language(work: Work) -> str | None:
    """Return the feed language of `work`, or None when unknown."""
    lang = work.extra.get(LANG_EXTRA_KEY)
    return lang if isinstance(lang, str) and lang else None


def parse_descriptions(payload: bytes, site: str, lang: str) -> dict[str, str]:
    """Map page title keys to descriptions from a wbgetentities reply."""
    try:
        data = json.loads(payload)
    except ValueError:
        logger.warning(f"Invalid JSON in Wikidata response for {site}")
        return {}
    if not isinstance(data, dict):
        logger.warning(
            f"Unexpected Wikidata response for {site}: {type(data).__name__}"
        )
        return {}
    if error := data.get("error"):
        logger.warning(f"Wikidata error for {site}: {error}")
        return {}
    entities = data.get("entities")
    if not isinstance(entities, dict):
        return {}
    descriptions: dict[str, str] = {}
    for entity in entities.values():
        if not isinstance(entity, dict):
            continue
        entity_descriptions = entity.get("descriptions")
        entity_sitelinks = entity.get("sitelinks")
        if not isinstance(entity_descriptions, dict) or not isinstance(
            entity_sitelinks, dict
        ):
            continue
        description = entity_descriptions.get(lang)
        sitelink = entity_sitelinks.get(site)
        if not isinstance(description, dict) or not isinstance(sitelink, dict):
            continue
        value = description.get("value")
        title = sitelink.get("title")
        if isinstance(value, str) and value and isinstance(title, str):
            descriptions[title_key(title)] = value
    return descriptions


def batch_titles(titles: list[str]) -> list[list[str]]:
    """Split `titles` into requests within the API title and URL length limits."""
    batches: list[list[str]] = []
    batch: list[str] = []
    length = 0
    for title in titles:
        encoded_length = len(urllib.parse.quote(f"{title}|", safe=""))
        if batch and (
            len(batch) == WIKIDATA_MAX_TITLES
            or length + encoded_length > WIKIDATA_MAX_QUERY_BYTES
        ):
            batches.append(batch)
            batch, length = [], 0
        batch.append(title)
        length += encoded_length
    if batch:
        batches.append(batch)
    return batches


def fetch_descriptions(
    engine: DownloadEngine, lang: str, titles: list[str]
) -> dict[str, str]:
    """Return {page title key: description} for one batch of page names."""
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
    grouped: dict[str, dict[str, list[Work]]] = {}
    for work in store.works:
        if work.description:
            continue
        lang = work_language(work)
        page = page_name(work)
        if lang and page:
            grouped.setdefault(lang, {}).setdefault(page, []).append(work)
    total = sum(
        len(works) for by_page in grouped.values() for works in by_page.values()
    )
    if not total:
        return

    logger.info(f"Looking up Wikidata descriptions for {total} Wikisource work(s)")
    enriched = 0
    for lang, by_page in grouped.items():
        for titles in batch_titles(list(by_page)):
            descriptions = fetch_descriptions(engine, lang, titles)
            for title in titles:
                description = descriptions.get(title_key(title))
                if not description:
                    continue
                for work in by_page[title]:
                    work.description = description
                    enriched += 1
    logger.info(f"Added Wikidata descriptions to {enriched} Wikisource work(s)")
