"""Turn ws-export's ``htmlz`` archive into ZIM-ready HTML pages.

ws-export exports a book as HTML by zipping a single ``index.html`` together
with its stylesheets and images. The archive is self-contained and uses
relative references, so serving it offline only needs two things: stable ZIM
paths for every member, and those references rewritten to point at them.

The root page is stored where the rest of the pipeline expects an HTML edition
(``article_name_for``), while the remaining members live under
``html/<work id>/``. Reader controls are injected so the page links back to the
book details and to the binary formats stored in the same ZIM.
"""

import mimetypes
import posixpath
import re
import zlib
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import unquote, urlsplit
from zipfile import BadZipFile, ZipFile

from bs4 import BeautifulSoup

from papers2zim.constants import logger
from papers2zim.core.exporters.html_reader_controls import (
    encode_url_path,
    inject_reader_controls,
)
from papers2zim.core.models import Work
from papers2zim.core.utils import article_name_for

MAX_HTMLZ_FILES = 500
MAX_HTMLZ_UNCOMPRESSED_BYTES = 64 * 1024 * 1024
HTML_SUFFIXES = (".html", ".htm", ".xhtml")
CSS_URL_PATTERN = re.compile(r"url\((?P<quote>['\"]?)(?P<url>[^)'\"]+)(?P=quote)\)")


@dataclass(frozen=True, slots=True)
class HtmlEdition:
    """ZIM pages of one HTML export, keyed by path, with their media types."""

    pages: dict[str, tuple[bytes, str]]
    index_path: str


def extract_html_edition(
    content: bytes, work: Work, formats: list[str]
) -> HtmlEdition | None:
    """Extract a ws-export ``htmlz`` archive into rendered ZIM pages.

    Returns ``None`` when the archive is not a valid HTML export, so the caller
    can record the format as unsupported for this work.
    """
    try:
        with ZipFile(BytesIO(content)) as archive:
            members = _read_members(archive, work)
            index_name = _find_index(members)
            if index_name is None:
                logger.warning("HTML export for %s has no index page", work.id)
                return None
            path_by_name = {
                name: _zim_path_for(work, name, index_name) for name in members
            }
            pages = {
                path_by_name[name]: _render_member(
                    name,
                    path_by_name[name],
                    data,
                    path_by_name,
                    work,
                    formats,
                )
                for name, data in members.items()
            }
    except BadZipFile, RuntimeError, NotImplementedError, zlib.error:
        # unreadable archive, encrypted member, unsupported compression, or a
        # corrupt entry: not an HTML export we can serve
        return None
    return HtmlEdition(pages=pages, index_path=path_by_name[index_name])


def _read_members(archive: ZipFile, work: Work) -> dict[str, bytes]:
    """Read regular files with bounded size, dropping unsafe member names."""
    infos = [info for info in archive.infolist() if not info.is_dir()]
    if len(infos) > MAX_HTMLZ_FILES:
        logger.warning(
            "HTML export for %s has %s files, more than the %s-file limit",
            work.id,
            len(infos),
            MAX_HTMLZ_FILES,
        )
        return {}
    members: dict[str, bytes] = {}
    total = 0
    for info in infos:
        name = _safe_member_name(info.filename)
        if name is None:
            logger.debug("Skipping unsafe HTML export member %r", info.filename)
            continue
        total += info.file_size
        if total > MAX_HTMLZ_UNCOMPRESSED_BYTES:
            logger.warning(
                "HTML export for %s is larger than %s MiB, skipping",
                work.id,
                MAX_HTMLZ_UNCOMPRESSED_BYTES // (1024 * 1024),
            )
            return {}
        members[name] = archive.read(info)
    return members


def _safe_member_name(name: str) -> str | None:
    """Reject absolute or parent-traversing archive member names."""
    parts = name.replace("\\", "/").split("/")
    if any(part == ".." for part in parts):
        return None
    clean = [part for part in parts if part not in ("", ".")]
    return "/".join(clean) if clean else None


def _find_index(members: dict[str, bytes]) -> str | None:
    """The archive's root HTML page: ``index.html`` when present."""
    for name in members:
        if posixpath.basename(name).casefold() == "index.html":
            return name
    return next(
        (name for name in members if name.casefold().endswith(HTML_SUFFIXES)), None
    )


def _zim_path_for(work: Work, name: str, index_name: str) -> str:
    if name == index_name:
        return article_name_for(work)
    return f"html/{work.id}/{name}"


def _render_member(
    name: str,
    zim_path: str,
    content: bytes,
    path_by_name: dict[str, str],
    work: Work,
    formats: list[str],
) -> tuple[bytes, str]:
    """Rewrite one archive member for offline use and return it with its type."""
    if name.casefold().endswith(HTML_SUFFIXES):
        return (
            _rewrite_html(content, name, zim_path, path_by_name, work, formats),
            "text/html",
        )
    if name.casefold().endswith(".css"):
        return _rewrite_css(content, name, zim_path, path_by_name), "text/css"
    return content, _guess_mimetype(name, content)


def _rewrite_html(
    content: bytes,
    name: str,
    zim_path: str,
    path_by_name: dict[str, str],
    work: Work,
    formats: list[str],
) -> bytes:
    soup = BeautifulSoup(content, "html.parser")
    for element in soup.find_all(True):
        for attribute in ("href", "src"):
            reference = element.get(attribute)
            if not isinstance(reference, str):
                continue
            rewritten = _rewrite_reference(reference, name, zim_path, path_by_name)
            if rewritten is not None:
                element[attribute] = rewritten
    inject_reader_controls(soup, zim_path, work, formats)
    return str(soup).encode("utf-8")


def _rewrite_css(
    content: bytes, name: str, zim_path: str, path_by_name: dict[str, str]
) -> bytes:
    css = content.decode("utf-8", errors="replace")

    def replace(match: re.Match[str]) -> str:
        rewritten = _rewrite_reference(match["url"], name, zim_path, path_by_name)
        if rewritten is None:
            return match.group(0)
        return f"url({match['quote']}{rewritten}{match['quote']})"

    return CSS_URL_PATTERN.sub(replace, css).encode("utf-8")


def _rewrite_reference(
    reference: str, name: str, zim_path: str, path_by_name: dict[str, str]
) -> str | None:
    """Rewrite a member-relative reference into a relative ZIM path."""
    target = _resolve_member(reference, name)
    if target is None:
        return None
    target_name, fragment = target
    target_path = path_by_name.get(target_name)
    if target_path is None:
        return None
    relative = encode_url_path(
        posixpath.relpath(target_path, posixpath.dirname(zim_path) or ".")
    )
    return f"{relative}#{fragment}" if fragment else relative


def _resolve_member(reference: str, name: str) -> tuple[str, str] | None:
    """Resolve a same-archive reference to a member name and its fragment."""
    reference = reference.strip()
    if not reference or reference.startswith(("#", "data:", "javascript:")):
        return None
    split = urlsplit(reference)
    if split.scheme or split.netloc:
        return None
    path = unquote(split.path)
    if not path:
        return None
    base = "" if path.startswith("/") else posixpath.dirname(name)
    target = posixpath.normpath(posixpath.join(base, path.lstrip("/")))
    if target == ".." or target.startswith("../"):
        return None
    return target, split.fragment


def _guess_mimetype(name: str, content: bytes) -> str:
    guessed, _encoding = mimetypes.guess_type(name, strict=False)
    if guessed:
        return guessed
    for magic, mimetype in (
        (b"\x89PNG\r\n\x1a\n", "image/png"),
        (b"\xff\xd8\xff", "image/jpeg"),
        (b"GIF87a", "image/gif"),
        (b"GIF89a", "image/gif"),
    ):
        if content.startswith(magic):
            return mimetype
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    if content.lstrip().startswith(b"<svg"):
        return "image/svg+xml"
    return "application/octet-stream"
