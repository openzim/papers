"""Open Textbook Library metadata access.

Fetches full textbook records from the OTL JSON REST API
(`GET /textbooks/{id}.json`) and exposes them through the source-agnostic
`MetadataPort` interface.

Unlike Gutenberg, licenses are per-book Creative Commons licenses. OTL's
review total is exported as the source-defined primary metric.
"""

import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import requests

from papers2zim.constants import logger
from papers2zim.core.download_engine import DownloadEngine, is_fatal_http_error
from papers2zim.core.models import CollectionRef, Creator, Format, Work
from papers2zim.core.ports import MetadataPort, WorkRef
from papers2zim.core.utils import atomic_write_text
from papers2zim.sources.opentextbooks.catalog import OTL_SOURCE, normalize_language

SUBJECTS_PATH = "/subjects.json"
SUBJECTS_CACHE_FILENAME = "otl_subjects.json"

# OTL format type -> media type (only the downloadable formats matter;
# "Online"/"XML"/"ODF" records are kept for completeness)
MEDIA_TYPES = {
    "PDF": "application/pdf",
    "eBook": "application/epub+zip",
    "Online": "text/html",
}


def _creator_from_contributor(contributor: dict[str, Any]) -> Creator:
    """Map an OTL contributor record to a Creator"""
    first = " ".join(
        part
        for part in (contributor.get("first_name"), contributor.get("middle_name"))
        if part
    )
    last = contributor.get("last_name")
    if contributor.get("corporate"):
        # corporate contributors carry the organisation name in last_name
        name = last or first or "Unknown"
        return Creator(id=str(contributor["id"]), display_name=name, sort_name=name)
    display_name = " ".join(part for part in (first, last) if part) or "Unknown"
    return Creator(
        id=str(contributor["id"]),
        display_name=display_name,
        sort_name=last,
    )


def _subject_root_map(tree: Any) -> dict[str, CollectionRef]:
    """Map every subject id to the collection of its top-level ancestor."""
    roots: dict[str, CollectionRef] = {}

    def visit(nodes: Any, root: CollectionRef | None) -> None:
        if not isinstance(nodes, list):
            return
        for node in nodes:
            if not isinstance(node, dict):
                continue
            subject_id = node.get("id")
            subject_name = node.get("name")
            if (
                subject_id is None
                or not isinstance(subject_name, str)
                or not subject_name
            ):
                continue
            collection = root or CollectionRef(
                id=str(subject_id), name=subject_name, kind="subject"
            )
            roots[str(subject_id)] = collection
            visit(node.get("child_subjects"), collection)

    visit(tree, None)
    return roots


def _root_subjects(
    record: dict[str, Any], subject_roots: dict[str, CollectionRef]
) -> list[CollectionRef]:
    """One collection per top-level subject tree the textbook belongs to.

    The subject tree is authoritative because a record only lists the subjects
    it was filed under, not necessarily their ancestors. Records remain the
    fallback when the tree could not be loaded.
    """
    subjects: dict[str, dict[str, Any]] = {}
    for subject in record.get("subjects") or []:
        if not isinstance(subject, dict):
            continue
        subject_id = subject.get("id")
        subject_name = subject.get("name")
        if subject_id is not None and isinstance(subject_name, str) and subject_name:
            subjects[str(subject_id)] = subject

    roots: dict[str, CollectionRef] = {}
    for subject_id, subject in subjects.items():
        root = subject_roots.get(subject_id)
        if root is None:
            node = subject
            seen: set[str] = set()
            while True:
                parent_id = node.get("parent_subject_id")
                parent_key = str(parent_id) if parent_id is not None else None
                if (
                    parent_key is None
                    or parent_key not in subjects
                    or parent_key in seen
                ):
                    break
                seen.add(parent_key)
                node = subjects[parent_key]
            root = CollectionRef(id=str(node["id"]), name=node["name"], kind="subject")
        roots.setdefault(root.id, root)
    return list(roots.values())


def _review_score(record: dict[str, Any]) -> float | None:
    """Return an aggregate OTL peer-review score with a confidence tie-breaker."""
    try:
        rating = float(record["rating"])
    except KeyError, TypeError, ValueError:
        return None
    try:
        review_count = int(record.get("textbook_reviews_count") or 0)
    except TypeError, ValueError:
        review_count = 0
    if review_count <= 0:
        return None
    # Rating remains decisive; up to 0.09 breaks ties in favour of a score
    # supported by more reviews without allowing quantity to outweigh quality.
    return rating + min(review_count, 9) / 100


class OpenTextbookLibraryMetadata(MetadataPort):
    """Fetches full OTL textbook records"""

    BASE_URL = "https://open.umn.edu/opentextbooks"

    def __init__(
        self,
        base_url: str = BASE_URL,
        *,
        engine: DownloadEngine,
        cache_dir: Path | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._engine = engine
        self._cache_dir = cache_dir.resolve() / "otl_metadata" if cache_dir else None
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._subject_roots: dict[str, CollectionRef] | None = None

    def fetch(self, refs: Iterable[WorkRef]) -> Iterator[Work]:
        subject_roots = self._load_subject_roots()
        for ref in refs:
            record = self._fetch_record(ref.id)
            if record is None:
                continue
            yield self._to_work(ref, record, subject_roots)

    def _load_subject_roots(self) -> dict[str, CollectionRef]:
        """Root collection of every subject, from the OTL subject tree."""
        if self._subject_roots is not None:
            return self._subject_roots
        cache_path = (
            self._cache_dir / SUBJECTS_CACHE_FILENAME if self._cache_dir else None
        )
        tree: Any = None
        if cache_path:
            try:
                tree = json.loads(cache_path.read_text(encoding="utf-8"))
            except OSError, json.JSONDecodeError:
                tree = None
        if tree is None:
            url = f"{self._base_url}{SUBJECTS_PATH}"
            try:
                payload = json.loads(self._engine.fetch_bytes(url))
            except requests.RequestException, json.JSONDecodeError:
                logger.warning(
                    "Could not load the OTL subject tree, collections fall back"
                    " to the subjects listed on each textbook"
                )
                payload = None
            tree = payload.get("data") if isinstance(payload, dict) else None
            if cache_path and tree is not None:
                atomic_write_text(cache_path, json.dumps(tree))
        self._subject_roots = _subject_root_map(tree) if tree else {}
        return self._subject_roots

    def _fetch_record(self, textbook_id: str) -> dict[str, Any] | None:
        """One textbook record, or None when OTL does not have it (404)"""
        cache_path = (
            self._cache_dir / f"{textbook_id}.json" if self._cache_dir else None
        )
        if cache_path:
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                if isinstance(cached, dict):
                    logger.debug(
                        "Using cached OTL metadata for textbook #%s", textbook_id
                    )
                    return cached
            except OSError, json.JSONDecodeError:
                pass
        url = f"{self._base_url}/textbooks/{textbook_id}.json"
        try:
            payload = json.loads(self._engine.fetch_bytes(url))
        except requests.RequestException as exc:
            if is_fatal_http_error(exc):
                logger.warning(f"OTL textbook #{textbook_id} not found, skipping")
                return None
            raise
        record = payload.get("data")
        if not isinstance(record, dict):
            logger.warning(f"OTL textbook #{textbook_id} has no data, skipping")
            return None
        if cache_path:
            atomic_write_text(cache_path, json.dumps(record))
        return record

    def _to_work(
        self,
        ref: WorkRef,
        record: dict[str, Any],
        subject_roots: dict[str, CollectionRef],
    ) -> Work:
        creators = [
            _creator_from_contributor(contributor)
            for contributor in record.get("contributors") or []
            if contributor.get("contribution") == "Author"
        ]
        language = normalize_language(record.get("language"))
        return Work(
            id=ref.id,
            source=OTL_SOURCE,
            title=record.get("title") or ref.extra.get("title") or "Untitled",
            creators=creators,
            languages=[language] if language else [],
            # per-book Creative Commons license (NOT uniform across books)
            license=record.get("license") or ref.extra.get("license"),
            formats=[
                Format(
                    name=format_type,
                    media_type=MEDIA_TYPES.get(format_type, "application/octet-stream"),
                    url=fmt.get("url"),
                )
                for fmt in record.get("formats") or []
                if isinstance(fmt, dict)
                and isinstance(format_type := fmt.get("type"), str)
                and format_type
            ],
            collections=_root_subjects(record, subject_roots),
            popularity=_review_score(record),
            description=record.get("description") or ref.extra.get("description"),
            source_url=record.get("url") or ref.extra.get("source_url"),
            extra={
                "otl_id": ref.id,
                "copyright_year": record.get("copyright_year")
                or ref.extra.get("copyright_year"),
                "isbn10": record.get("isbn10") or ref.extra.get("isbn10"),
                "isbn13": record.get("isbn13") or ref.extra.get("isbn13"),
                "review_rating": record.get("rating"),
                "review_count": _review_count(record),
            },
        )


def _review_count(record: dict[str, Any]) -> int:
    """Return OTL's faculty-review total, tolerating malformed API values."""
    try:
        return int(record.get("textbook_reviews_count") or 0)
    except TypeError, ValueError:
        return 0
