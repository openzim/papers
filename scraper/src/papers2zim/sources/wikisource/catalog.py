"""OPDS-backed Wikisource discovery.

ws-export (https://ws-export.wmcloud.org) publishes, per Wikisource language, an
OPDS Atom feed of the books flagged "ready for export". Each feed lives under
``/opds/<lang>/`` with a language-specific filename, so discovery reads the
directory index to find it, then parses its ``<entry>`` elements.

The filename is the only thing naming the feed, and it is localized -
``Ready_for_export.xml`` on en, ``Bon_pour_export.xml`` on fr - so it cannot be
hardcoded nor recognized language-independently. Discovery therefore relies on
ws-export advertising exactly one feed per language, which is what it does
today, and refuses to guess between several: a second feed would be ingested
alongside the first, adding unrelated works with no way to tell they are
unrelated. Pass ``--wikisource-feed`` to name the feed to use in that case; since
the name belongs to one language, it only disambiguates - where a language
advertises a single feed, that feed is read whatever was passed.

Every entry is self-contained: it carries the title, author, language, license,
year, source page and one ready-made ws-export download link per format. So a
`WorkRef` here already holds everything the metadata port needs - no per-book
fetch, unlike Open Textbook Library.
"""

import hashlib
from collections.abc import Iterable
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup, Tag

from papers2zim.constants import logger
from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.ports import CatalogFilters, CatalogPort, WorkRef
from papers2zim.core.utils import critical_error, slugify

WIKISOURCE_SOURCE = "wikisource"
BASE_URL = "https://ws-export.wmcloud.org"

# OPDS acquisition media type -> the format name used across the pipeline.
FORMAT_BY_MEDIA_TYPE = {
    "application/epub+zip": "epub",
}

ACQUISITION_REL = "http://opds-spec.org/acquisition"


def work_id(lang: str, page: str) -> str:
    """A path-safe id, unique per (language, page), readable where possible.

    `page` is the ws-export page name (percent-encoded, as it appears in the
    source URL); the short digest guarantees uniqueness when slugs collide or
    the title becomes empty.
    """
    slug = slugify(unquote(page), max_encoded_length=80)
    digest = hashlib.sha256(f"{lang}:{page}".encode()).hexdigest()[:8]
    return f"{lang}_{slug}-{digest}" if slug else f"{lang}_{digest}"


def page_key(page: str) -> str:
    """Normalize a page name so URL and display forms compare equal."""
    return unquote(page).strip().replace(" ", "_")


def feed_key(name: str) -> str:
    """Normalize a feed reference to its bare file name, for `--wikisource-feed`."""
    name = unquote(name.rsplit("/", 1)[-1]).strip()
    if name.casefold().endswith(".xml"):
        name = name[: -len(".xml")]
    return name.casefold()


class WikisourceCatalog(CatalogPort):
    """Discover Wikisource books from ws-export's per-language OPDS feeds."""

    def __init__(
        self,
        engine: DownloadEngine,
        base_url: str = BASE_URL,
        **_: object,
    ):
        self._engine = engine
        self._base_url = base_url.rstrip("/")

    def discover(self, filters: CatalogFilters) -> Iterable[WorkRef]:
        languages = [lang.lower() for lang in (filters.languages or [])]
        if not languages:
            critical_error(
                "Wikisource is organised per language; pass one or more codes "
                "via --languages (e.g. --languages=en,fr)."
            )

        requested_formats = set(filters.formats) if filters.formats else None
        feed_name = filters.options.get("feed")
        refs: list[WorkRef] = []
        advertised_formats: set[str] = set()
        for lang in languages:
            lang_refs, lang_advertised_formats = self._discover_language(
                lang, requested_formats, feed_name
            )
            refs.extend(lang_refs)
            advertised_formats |= lang_advertised_formats

        if requested_formats is not None:
            missing_formats = requested_formats - advertised_formats
            if missing_formats:
                critical_error(
                    f"Requested formats not available from ws-export: "
                    f"{', '.join(sorted(missing_formats))}. "
                    f"ws-export offers: {', '.join(sorted(advertised_formats))}."
                )

        pages = filters.options.get("pages")
        if pages:
            selected = self._select_pages(refs, pages)
        else:
            selected = self._select_positions(refs, filters.book_ids)
        logger.info(
            "  Selected %s Wikisource books from %s catalog entries (languages: %s)",
            len(selected),
            len(refs),
            ", ".join(languages),
        )
        return selected

    def _discover_language(
        self,
        lang: str,
        requested_formats: set[str] | None,
        feed_name: str | None,
    ) -> tuple[list[WorkRef], set[str]]:
        refs: list[WorkRef] = []
        advertised_formats: set[str] = set()
        for feed_url in self._feed_urls(lang, feed_name):
            feed = BeautifulSoup(self._engine.fetch_bytes(feed_url), "xml")
            if feed.find("feed") is None:
                critical_error(
                    f"{feed_url} is not an OPDS feed: it holds no Atom <feed> "
                    "element. ws-export is serving something else under this name."
                )
            for entry in feed.find_all("entry"):
                if not isinstance(entry, Tag):
                    continue
                extra = self._parse_entry(entry, lang)
                if extra is None:
                    continue
                entry_advertised_formats = {
                    name for name, _mt, _url in extra["formats"]
                }
                advertised_formats |= entry_advertised_formats
                if requested_formats is not None and not (
                    requested_formats & entry_advertised_formats
                ):
                    continue
                refs.append(
                    WorkRef(
                        id=work_id(lang, extra["page"]),
                        source=WIKISOURCE_SOURCE,
                        extra=extra,
                    )
                )
        return refs, advertised_formats

    def _feed_urls(self, lang: str, feed_name: str | None) -> list[str]:
        index_url = f"{self._base_url}/opds/{lang}/"
        try:
            index = self._engine.fetch_bytes(index_url).decode("utf-8", "replace")
        except requests.RequestException as exc:
            logger.warning(
                "No Wikisource OPDS index for language %r, skipping (%s)", lang, exc
            )
            return []
        soup = BeautifulSoup(index, "html.parser")
        discovered = [
            urljoin(index_url, href)
            for anchor in soup.find_all("a", href=True)
            if isinstance(anchor, Tag)
            and (href := str(anchor["href"])).lower().endswith(".xml")
        ]
        if not discovered:
            logger.warning("No OPDS feed found under %s", index_url)
            return []
        if len(discovered) > 1 and not feed_name:
            critical_error(
                f"{index_url} advertises {len(discovered)} OPDS feeds "
                f"({', '.join(_file_names(discovered))}). Their names are localized, "
                "so which one holds the ready-for-export books cannot be told from "
                "them, and reading them all would ingest entries we cannot "
                "attribute. Pass the one to use with --wikisource-feed."
            )
        if not feed_name:
            return discovered
        wanted = feed_key(feed_name)
        matching = [url for url in discovered if feed_key(url) == wanted]
        if matching:
            return matching
        if len(discovered) == 1:
            logger.warning(
                "--wikisource-feed=%s is not advertised under %s; reading its only "
                "feed (%s). Feed names are per language, so a name meant for one "
                "language does not select another's.",
                feed_name,
                index_url,
                _file_names(discovered)[0],
            )
            return discovered
        critical_error(
            f"--wikisource-feed={feed_name} is not advertised under {index_url} "
            f"(offered: {', '.join(_file_names(discovered))})"
        )

    @staticmethod
    def _parse_entry(entry: Tag, lang: str) -> dict | None:
        source = _text(entry, "source") or _text(entry, "id")
        title = _text(entry, "title")
        if not source or not title:
            return None
        page = source.rsplit("/wiki/", 1)[-1]

        formats: list[tuple[str, str, str]] = []
        for link in entry.find_all("link"):
            if not isinstance(link, Tag) or link.get("rel") != ACQUISITION_REL:
                continue
            media_type = str(link.get("type") or "")
            href = link.get("href")
            if not href:
                continue
            name = FORMAT_BY_MEDIA_TYPE.get(media_type)
            if name is None:
                continue
            formats.append((name, media_type, str(href)))
        if not formats:
            return None

        author = entry.find("author")
        return {
            "title": title,
            "author": _text(author, "name") if isinstance(author, Tag) else None,
            "language": _text(entry, "language") or lang,
            "license": _text(entry, "rights"),
            "source_url": source,
            "issued": _text(entry, "issued"),
            "page": page,
            "lang": lang,
            "formats": formats,
        }

    @staticmethod
    def _select_pages(refs: list[WorkRef], pages: list[str]) -> list[WorkRef]:
        wanted = {page_key(page) for page in pages}
        selected = [ref for ref in refs if page_key(ref.extra["page"]) in wanted]
        found = {page_key(ref.extra["page"]) for ref in selected}
        for page in pages:
            if page_key(page) not in found:
                logger.warning(
                    "Wikisource page %s is not in the ws-export feed for the "
                    "requested languages and formats, skipping",
                    page,
                )
        return selected

    @staticmethod
    def _select_positions(
        refs: list[WorkRef], book_ids: list[str] | None
    ) -> list[WorkRef]:
        if not book_ids:
            return refs
        positions = set()
        for book_id in book_ids:
            try:
                positions.add(int(book_id))
            except ValueError:
                continue
        if not positions:
            return refs
        return [
            ref for position, ref in enumerate(refs, start=1) if position in positions
        ]


def _file_names(urls: list[str]) -> list[str]:
    """Feed file names, decoded: the index hrefs are percent-encoded."""
    return [unquote(url.rsplit("/", 1)[-1]) for url in urls]


def _text(parent: Tag | None, name: str) -> str | None:
    if parent is None:
        return None
    tag = parent.find(name)
    if not isinstance(tag, Tag):
        return None
    text = tag.get_text(strip=True)
    return text or None
