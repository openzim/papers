"""One More Library book metadata parsed from individual book pages."""

import re
from collections.abc import Iterable, Iterator
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from papers2zim.constants import logger
from papers2zim.core.download_engine import DownloadEngine, is_fatal_http_error
from papers2zim.core.models import CollectionRef, Cover, Creator, Format, Work
from papers2zim.core.ports import MetadataPort, WorkRef
from papers2zim.core.utils import atomic_write_text
from papers2zim.sources.onemorelibrary.catalog import OML_SOURCE
from papers2zim.sources.onemorelibrary.languages import language_code

FORMAT_MEDIA_TYPES = {
    "epub": "application/epub+zip",
    "pdf": "application/pdf",
}
_AUTHOR_ID_RE = re.compile(r"-(\d+)$")
_BOOKS_SUFFIX_RE = re.compile(r"\s*\(\s*\d+\s*books?\s*\)\s*$", re.IGNORECASE)


def _text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split())


def _row_values(soup: BeautifulSoup, container: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for row in soup.select(f"{container} .row"):
        label = row.select_one(".row_label")
        value = row.select_one(".row_value")
        if label is None or value is None:
            continue
        key = _text(label).rstrip(":").strip()
        if key:
            values[key] = _text(value)
    return values


def _additional_details(
    soup: BeautifulSoup,
) -> tuple[dict[str, str], list[CollectionRef]]:
    """Read the ``.additional`` block once, returning its values and categories."""
    values: dict[str, str] = {}
    collections: list[CollectionRef] = []
    for row in soup.select(".additional .row"):
        label = row.select_one(".row_label")
        value = row.select_one(".row_value")
        if label is None or value is None:
            continue
        key = _text(label).rstrip(":").strip()
        if not key:
            continue
        if key == "In categories":
            for link in value.select("a[href]"):
                href = link.get("href")
                if not isinstance(href, str):
                    continue
                collections.append(
                    CollectionRef(
                        id=urlparse(href).path.rstrip("/").rsplit("/", 1)[-1],
                        name=_text(link),
                        kind="category",
                    )
                )
            continue
        values[key] = _text(value)
    return values, collections


def _creator(soup: BeautifulSoup) -> Creator | None:
    anchor = soup.select_one(".profile_name_data h2 a.profile_name")
    if anchor is None:
        anchor = soup.select_one(".profile_name_data a.profile_name")
    if anchor is None:
        return None
    name = _BOOKS_SUFFIX_RE.sub("", _text(anchor)).strip()
    if not name:
        return None
    href = anchor.get("href")
    author_id = None
    sort_name = None
    first_names = None
    if isinstance(href, str):
        match = _AUTHOR_ID_RE.search(urlparse(href).path)
        if match is not None:
            author_id = match.group(1)
        slug = _AUTHOR_ID_RE.sub("", urlparse(href).path.rstrip("/").rsplit("/", 1)[-1])
        parts = [part for part in slug.split("-") if part]
        if len(parts) > 1:
            first_names = " ".join(parts[:-1]).title()
            sort_name = parts[-1].title()
        elif parts:
            sort_name = parts[0].title()
    wikipedia = soup.select_one(".row_wikipedia a[href]")
    wikipedia_url = wikipedia.get("href") if wikipedia is not None else None
    return Creator(
        id=author_id or name.casefold().replace(" ", "-"),
        name=name,
        sort_name=sort_name,
        extra={
            "first_names": first_names,
            "author_url": href if isinstance(href, str) else None,
            "wikipedia_url": wikipedia_url if isinstance(wikipedia_url, str) else None,
        },
    )


def _formats(soup: BeautifulSoup, page_url: str) -> tuple[list[Format], int]:
    formats: list[Format] = []
    hits_total = 0
    for size_info in soup.select(".attachments .djc_filesize"):
        row = size_info.find_parent(class_="row")
        if row is None:
            continue
        link = row.select_one("a[href*='fid=']")
        if link is None:
            continue
        href = link.get("href")
        if not isinstance(href, str):
            continue
        parts = [part.strip() for part in _text(size_info).split("|")]
        if not parts:
            continue
        format_name = parts[0].lower()
        if len(parts) >= 3:  # noqa: PLR2004  "epub | 9.72 KB | 440 hits"
            hits = re.sub(r"\D", "", parts[-1])
            if hits:
                hits_total += int(hits)
        media_type = FORMAT_MEDIA_TYPES.get(format_name)
        if media_type is None:
            continue
        formats.append(
            Format(
                name=format_name,
                media_type=media_type,
                url=urljoin(page_url, href),
            )
        )
    return formats, hits_total


def _cover_url(soup: BeautifulSoup, page_url: str) -> str | None:
    image = soup.select_one("#djc_mainimage[src]")
    if image is not None and isinstance(image.get("src"), str):
        return urljoin(page_url, str(image["src"]))
    meta = soup.select_one("meta[property='og:image'][content]")
    if meta is not None and isinstance(meta.get("content"), str):
        return urljoin(page_url, str(meta["content"]))
    return None


def parse_book_page(
    html: str | bytes, ref: WorkRef, page_url: str | None = None
) -> Work | None:
    """Parse one book page into a :class:`Work`."""
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.select_one(".title_top h1") or soup.select_one("h1")
    if title_node is None:
        return None
    title = _text(title_node)
    source_url = page_url or ref.extra.get("source_url")
    if not isinstance(source_url, str) or not source_url:
        return None

    details = _row_values(soup, ".custom_det")
    additional, collections = _additional_details(soup)
    language_node = soup.select_one(".title_top .type_button")
    language_name = (
        _text(language_node)
        if language_node is not None
        else ref.extra.get("language_name")
    )
    code = language_code(language_name)
    if language_name and code is None:
        logger.debug("Unknown One More Library language label: %s", language_name)

    formats, hits = _formats(soup, source_url)
    if not collections and ref.extra.get("category_id"):
        collections = [
            CollectionRef(
                id=str(ref.extra["category_id"]),
                name=str(ref.extra.get("category_name") or ref.extra["category_id"]),
                kind="category",
            )
        ]

    creator = _creator(soup)
    cover = _cover_url(soup, source_url)
    license_name = details.get("License") or "Public domain"

    return Work(
        id=str(additional.get("Book ID") or ref.id),
        source=OML_SOURCE,
        title=title or ref.extra.get("title") or "Untitled",
        creators=[creator] if creator is not None else [],
        languages=[code] if code else [],
        license=license_name,
        formats=formats,
        cover=Cover(source_url=cover) if cover else None,
        collections=collections,
        popularity=hits or None,
        description=ref.extra.get("description") or None,
        published=details.get("Year of first publication"),
        source_url=source_url,
        extra={
            "book_id": str(additional.get("Book ID") or ref.id),
            "language_name": language_name,
            "translator": details.get("Translator"),
            "edition": details.get("Edition"),
            "notes": details.get("Notes"),
            "last_revision": details.get("Last revision"),
            "author_url": (
                urljoin(source_url, creator.extra["author_url"])
                if creator is not None and creator.extra.get("author_url")
                else None
            ),
        },
    )


class OnemorelibraryMetadata(MetadataPort):
    """Fetch and parse One More Library book pages."""

    def __init__(
        self,
        base_url: str,
        *,
        engine: DownloadEngine,
        cache_dir: Path | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._engine = engine
        self._cache_dir = (
            cache_dir.resolve() / "onemorelibrary_metadata" if cache_dir else None
        )
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self, refs: Iterable[WorkRef]) -> Iterator[Work]:
        for ref in refs:
            source_url = ref.extra.get("source_url")
            if not isinstance(source_url, str) or not source_url:
                logger.warning("One More Library book #%s has no source URL", ref.id)
                continue
            html = self._fetch_page(ref.id, source_url)
            if html is None:
                continue
            work = parse_book_page(html, ref, source_url)
            if work is None:
                logger.warning(
                    "One More Library book #%s has no parsable title, skipping",
                    ref.id,
                )
                continue
            yield work

    def _fetch_page(self, book_id: str, url: str) -> str | None:
        cache_path = self._cache_dir / f"{book_id}.html" if self._cache_dir else None
        if cache_path and cache_path.exists():
            try:
                logger.debug("Using cached One More Library metadata for #%s", book_id)
                return cache_path.read_text(encoding="utf-8")
            except OSError:
                pass
        try:
            content = self._engine.fetch_bytes(url)
        except requests.RequestException as exc:
            if is_fatal_http_error(exc):
                logger.warning(
                    "One More Library book #%s not found at %s, skipping",
                    book_id,
                    url,
                )
                return None
            raise
        html = content.decode("utf-8", errors="replace")
        if cache_path:
            atomic_write_text(cache_path, html)
        return html
