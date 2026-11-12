"""Wikipedia-backed author enrichment (biography and portrait).

A source opts into author enrichment by subclassing `WikipediaAuthorEnricher`
and implementing `resolve_articles`, which maps one of its `Creator`s to the
Wikipedia article(s) describing that author. The base class handles everything
else:

- resolving the article in the language the ZIM is built in first, through
  Wikipedia's interlanguage links, then falling back to the article the source
  resolved;
- fetching the Wikipedia REST summary, which carries both the plain-text
  introduction (`extract`) and the portrait thumbnail in one response;
- storing that portrait in the ZIM as WebP under `authors/{creator id}.webp`;
- deduplicating creators across works and fetching them concurrently.

Using the REST summary endpoint (page/summary) rather than the MediaWiki Action
API keeps the per-author request count low: the endpoint is designed for this
exact need and needs none of the parse/query boilerplate (templates, revisions,
prop selection) the Action API requires. The Action API is only used for the
interlanguage lookup, which the REST endpoint has no equivalent for.

`resolve_articles` returns an iterable of `(language, title)`, tried in order
and consumed lazily: a source can yield an authoritative article first and only
look up an alternative if that article turned out to lack the requested
details. Sources without a reliable article for an author yield nothing, so a
scrape never depends on Wikipedia being reachable, and authors with no article
are left untouched.

A ZIM spanning several languages has no single author-detail language to target,
so such a ZIM keeps using the resolved articles alone.
"""

import json
import re
import urllib.parse
from abc import ABC, abstractmethod
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

# A Wikipedia article as (language subdomain, article title)
WikipediaArticle = tuple[str, str]


def wikipedia_lang(code: str) -> str:
    """Return the Wikipedia subdomain code for an ISO 639 language code."""
    return ISO_MATRIX_REV.get(code, code)


def article_from_url(url: str | None) -> WikipediaArticle | None:
    """Return the (language, title) of a Wikipedia article URL, if it is one."""
    if not url:
        return None
    match = WIKIPEDIA_ARTICLE_RE.match(url)
    if not match:
        return None
    return match["lang"].lower(), urllib.parse.unquote(match["title"])


def zim_language(languages: Iterable[str] | None) -> str | None:
    """Return the Wikipedia code for a ZIM built in one single language.

    A ZIM spanning several languages has no single author-detail language to
    target, so nothing is returned and the resolved article is used as-is.
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
    if not isinstance(summary, dict):
        return None
    if summary.get("type") == "disambiguation" or "extract" not in summary:
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
    if not isinstance(payload, dict):
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
    engine: DownloadEngine, article: WikipediaArticle, language: str | None
) -> list[WikipediaArticle]:
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
        logger.warning(
            f"Failed to fetch or store portrait for {creator.display_name}: {exc}"
        )
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


class WikipediaAuthorEnricher(ABC):
    """Base class for source-specific Wikipedia author enrichment."""

    def __init__(
        self,
        engine: DownloadEngine,
        assembler: ZimAssembler,
        *,
        with_bio: bool = True,
        with_portrait: bool = True,
        concurrency: int = 1,
        language: str | None = None,
    ):
        self.engine = engine
        self.assembler = assembler
        self.with_bio = with_bio
        self.with_portrait = with_portrait
        self.concurrency = concurrency
        self.language = language

    @abstractmethod
    def resolve_articles(self, creator: Creator) -> Iterable[WikipediaArticle]:
        """Return the Wikipedia articles to try for `creator`, preferred first."""
        ...

    def enrich_creator(self, creator: Creator) -> Creator:
        """Return `creator` enriched with bio and/or portrait when available."""
        if not self.with_bio and not self.with_portrait:
            return creator

        extra = dict(creator.extra)
        has_bio = not self.with_bio
        has_portrait = not self.with_portrait

        articles = iter(self.resolve_articles(creator))
        while not (has_bio and has_portrait):
            article = next(articles, None)
            if article is None:
                break
            for lang, title in article_candidates(self.engine, article, self.language):
                if has_bio and has_portrait:
                    break
                summary = fetch_author_summary(self.engine, lang, title)
                if not summary:
                    continue
                if not has_bio:
                    extract = summary.get("extract")
                    if isinstance(extract, str) and extract.strip():
                        extra["bio"] = extract
                        has_bio = True
                if not has_portrait and (source := portrait_source(summary)):
                    if store_portrait(creator, self.engine, self.assembler, source):
                        extra["portrait_path"] = PORTRAIT_PATH_TEMPLATE.format(
                            id=creator.id
                        )
                        has_portrait = True

        return (
            replace(creator, extra=extra) if extra != dict(creator.extra) else creator
        )

    def enrich_authors(self, store: WorkStore) -> None:
        """Fetch bio and/or portrait for every author the source can resolve."""
        if not self.with_bio and not self.with_portrait:
            return

        works = list(store.works)
        unique: dict[str, Creator] = {}
        for work in works:
            for creator in work.creators:
                unique.setdefault(creator.id, creator)

        creators = list(unique.values())
        logger.info(
            f"Enriching {len(creators)} author(s) from Wikipedia"
            + (f", preferring {self.language}" if self.language else "")
        )

        results: dict[str, Creator] = {}
        results_lock = Lock()

        def enrich_entry(creator: Creator) -> None:
            enriched = self.enrich_creator(creator)
            with results_lock:
                results[creator.id] = enriched

        parallel_map(enrich_entry, creators, self.concurrency)

        for work in works:
            work.creators = [
                results.get(creator.id, creator) for creator in work.creators
            ]
