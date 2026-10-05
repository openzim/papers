"""Author details enrichment for Gutenberg works (bio + portrait).

When the `--with-author-bio` and/or `--with-author-portrait` options are
enabled, the Gutenberg pipeline enriches every author with a short biography
and/or a portrait sourced from Wikipedia.

The pivot from a Gutenberg author id to its Wikipedia article is the
`pgterms:webpage` link that Project Gutenberg curates inside the author
`pgterms:agent` block of the per-book RDF (see `sources.gutenberg.metadata`).
A single call to the Wikipedia REST summary endpoint yields both the
biography intro (`extract`) and the portrait thumbnail URL. This avoids any
ambiguous-name matching and keeps the number of Wikipedia requests to at
most one per author.

We use the Wikipedia REST summary endpoint (page/summary) rather than the
MediaWiki Action API because it is the endpoint designed for this exact need:
it returns the article's plain-text intro and, when relevant, the portrait
thumbnail in a single well-defined JSON response, without the parse/query
boilerplate (templates, revisions, prop selection) the Action API requires.

Project Gutenberg curates `pgterms:webpage` in whichever language it happens
to know best, which is the English Wikipedia even for a book written in
another language. Enrichment therefore targets the language the ZIM is built
in first, resolving the matching article through Wikipedia's own interlanguage
links, and only then falls back to the curated link. The fallback earns its
keep on its own: a localized article frequently carries no portrait, so the
English picture is still worth using.

A ZIM spanning several languages has no single author-detail language to
target, so such a ZIM keeps using the curated link alone.

The Action API is used for that interlanguage lookup alone, the REST summary
endpoint having no equivalent.

Authors without a Wikipedia link are left untouched, so a scrape never
depends on Wikipedia being reachable.
"""

import json
import re
import urllib.parse
from collections.abc import Iterable
from dataclasses import replace
from threading import Lock

import requests

from papers2zim.constants import logger
from papers2zim.core.concurrency import parallel_map
from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.language import ISO_MATRIX_REV
from papers2zim.core.models import Creator
from papers2zim.core.rewriters.image_rewriter import ImageProcessor
from papers2zim.core.work_store import WorkStore
from papers2zim.core.zim_assembler import ZimAssembler

WIKIPEDIA_SUMMARY_URL = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"

WIKIPEDIA_LANGLINKS_URL = (
    "https://{lang}.wikipedia.org/w/api.php?action=query&prop=langlinks"
    "&titles={title}&lllang={target}&lllimit=1&llprop=lang%7Ctitle"
    "&format=json&redirects=1"
)

WIKIPEDIA_ARTICLE_RE = re.compile(
    r"^https?://(?P<lang>[a-z0-9-]+)\.(?:m\.)?wikipedia\.org/wiki/(?P<title>.+)$",
    re.I,
)

PORTRAIT_PATH_TEMPLATE = "authors/{id}.webp"


def wikipedia_lang(code: str) -> str:
    """Return the Wikipedia subdomain code for a Gutenberg language code."""
    return ISO_MATRIX_REV.get(code, code)


def wikipedia_article(creator: Creator) -> tuple[str, str] | None:
    """Return the (language, title) of the Wikipedia article PG curated."""
    webpage = creator.extra.get("webpage_resource")
    if not webpage:
        return None
    match = WIKIPEDIA_ARTICLE_RE.match(webpage)
    if not match:
        return None
    return match["lang"].lower(), urllib.parse.unquote(match["title"])


def zim_language(languages: Iterable[str] | None) -> str | None:
    """Return the Wikipedia code for a ZIM built in one single language.

    A ZIM spanning several languages has no single author-detail language to
    target, so nothing is returned and the curated link is used as-is.
    """
    requested = [language for language in languages or [] if language]
    if len(requested) != 1:
        return None
    return wikipedia_lang(requested[0])


def fetch_author_summary(engine: DownloadEngine, lang: str, title: str) -> dict | None:
    """Return the Wikipedia REST summary JSON for `title`, or None on failure."""
    url = WIKIPEDIA_SUMMARY_URL.format(
        lang=lang, title=urllib.parse.quote(title, safe="()")
    )
    try:
        response = engine.fetch_bytes(url)
    except requests.RequestException as exc:
        logger.warning(f"Failed to fetch {lang} Wikipedia summary for {title}: {exc}")
        return None
    try:
        summary = json.loads(response)
    except ValueError:
        logger.warning(f"Invalid JSON in Wikipedia summary for {title}")
        return None
    if "extract" not in summary:
        return None
    return summary


def fetch_langlink_title(
    engine: DownloadEngine, lang: str, title: str, target: str
) -> str | None:
    """Return the `target`-language title a Wikipedia article links to."""
    url = WIKIPEDIA_LANGLINKS_URL.format(
        lang=lang,
        title=urllib.parse.quote(title, safe="()"),
        target=urllib.parse.quote(target),
    )
    try:
        response = engine.fetch_bytes(url)
    except requests.RequestException as exc:
        logger.warning(f"Failed to fetch {target} link for {title}: {exc}")
        return None
    try:
        payload = json.loads(response)
    except ValueError:
        logger.warning(f"Invalid JSON in {target} link lookup for {title}")
        return None
    pages = payload.get("query", {}).get("pages", {})
    if not isinstance(pages, dict):
        return None
    for page in pages.values():
        for langlink in page.get("langlinks", []):
            linked = langlink.get("title") or langlink.get("*")
            if isinstance(linked, str) and linked:
                return linked
    return None


def article_candidates(
    engine: DownloadEngine, article: tuple[str, str], language: str | None
) -> list[tuple[str, str]]:
    """Return the articles to try for an author, preferred one first."""
    lang, title = article
    candidates = []
    if language and language != lang:
        localized = fetch_langlink_title(engine, lang, title, language)
        if localized:
            candidates.append((language, localized))
    candidates.append((lang, title))
    return candidates


def store_portrait(
    creator: Creator,
    engine: DownloadEngine,
    assembler: ZimAssembler,
    source: str,
) -> bool:
    """Download and store a portrait for `creator`, True once stored."""
    portrait_path = PORTRAIT_PATH_TEMPLATE.format(id=creator.id)
    try:
        data = engine.fetch_bytes(source)
        # Wikipedia serves a raster thumbnail; store it as WebP like covers
        data = ImageProcessor.optimize_image_content(data)
    except (requests.RequestException, OSError, ValueError) as exc:
        logger.warning(f"Failed to fetch or store portrait for {creator.name}: {exc}")
        return False
    assembler.add_item_for(
        path=portrait_path,
        content=data,
        mimetype="image/webp",
        is_front=False,
    )
    return True


def portrait_source(summary: dict) -> str | None:
    """Return the portrait URL a Wikipedia summary points at, if any."""
    image = summary.get("thumbnail") or summary.get("originalimage")
    source = image.get("source") if isinstance(image, dict) else None
    return source if isinstance(source, str) and source else None


def enrich_creator(
    creator: Creator,
    engine: DownloadEngine,
    assembler: ZimAssembler,
    *,
    with_bio: bool = True,
    with_portrait: bool = True,
    language: str | None = None,
) -> Creator:
    """Return `creator` enriched with bio and/or portrait when available."""
    if not with_bio and not with_portrait:
        return creator
    article = wikipedia_article(creator)
    if not article:
        return creator

    extra = dict(creator.extra)
    has_bio = not with_bio
    has_portrait = not with_portrait

    for lang, title in article_candidates(engine, article, language):
        if has_bio and has_portrait:
            break
        summary = fetch_author_summary(engine, lang, title)
        if not summary:
            continue
        if not has_bio:
            extract = summary.get("extract")
            if isinstance(extract, str) and extract.strip():
                extra["bio"] = extract
                has_bio = True
        if not has_portrait and (source := portrait_source(summary)):
            if store_portrait(creator, engine, assembler, source):
                extra["portrait_path"] = PORTRAIT_PATH_TEMPLATE.format(id=creator.id)
                has_portrait = True

    return replace(creator, extra=extra) if extra != dict(creator.extra) else creator


def enrich_authors(
    store: WorkStore,
    engine: DownloadEngine,
    assembler: ZimAssembler,
    *,
    with_bio: bool = True,
    with_portrait: bool = True,
    concurrency: int,
    language: str | None = None,
) -> None:
    """Fetch bio and/or portrait for every author that has a Wikipedia page."""
    if not with_bio and not with_portrait:
        return

    works = list(store.works)
    unique: dict[str, Creator] = {}
    for work in works:
        for creator in work.creators:
            unique.setdefault(creator.id, creator)

    creators = list(unique.values())
    logger.info(
        f"Enriching {len(creators)} author(s) from Wikipedia"
        + (f", preferring {language}" if language else "")
    )

    results: dict[str, Creator] = {}
    results_lock = Lock()

    def enrich_entry(creator: Creator) -> None:
        enriched = enrich_creator(
            creator,
            engine,
            assembler,
            with_bio=with_bio,
            with_portrait=with_portrait,
            language=language,
        )
        with results_lock:
            results[creator.id] = enriched

    parallel_map(enrich_entry, creators, concurrency)

    for work in works:
        work.creators = [results.get(creator.id, creator) for creator in work.creators]
