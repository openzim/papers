"""USAID DEC Archive metadata access.

Catalog discovery already carries the dataset CSV metadata for each report,
so fetching a work is a direct conversion from the catalog reference.
"""

import hashlib
from collections.abc import Iterable, Iterator
from pathlib import Path

from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.models import CollectionRef, Creator, Format, Work
from papers2zim.core.ports import MetadataPort, WorkRef
from papers2zim.core.utils import slugify
from papers2zim.sources.usaiddec.catalog import DEFAULT_CATALOG_URL, USAIDDEC_SOURCE
from papers2zim.sources.usaiddec.collections import (
    collection_for,
    collection_slug,
)


def _author_id(name: str) -> str:
    """Deterministic id shared by every work of the same author.

    Python's built-in ``hash`` is randomized per process, so it cannot be used
    here: it would give the same author a different id on every run, making
    author pages and their work counts non-reproducible.
    """
    normalized = " ".join(name.split())
    slug = slugify(normalized, max_encoded_length=80)
    digest = hashlib.sha256(normalized.casefold().encode()).hexdigest()[:8]
    return f"{slug}-{digest}" if slug else digest


def _sort_name(name: str) -> str:
    """Surname from the AidData ``Personal Author`` ``"Last, First"`` format."""
    last, separator, _ = name.partition(",")
    if separator and last.strip():
        return last.strip()
    parts = name.split()
    return parts[-1] if parts else name


def _author_creators(names: list[str]) -> list[Creator]:
    creators: list[Creator] = []
    for raw_name in names:
        name = " ".join(raw_name.split())
        if not name:
            continue
        creators.append(
            Creator(
                id=_author_id(name),
                display_name=name,
                sort_name=_sort_name(name),
            )
        )
    return creators


def _collections(class_name: str | None, subjects: list[str]) -> list[CollectionRef]:
    """Attach the report to exactly one curated thematic collection."""
    name = collection_for(class_name, subjects)
    return [
        CollectionRef(
            id=collection_slug(name),
            name=name,
            kind="subject",
        )
    ]


class UsaidDecMetadata(MetadataPort):
    """Builds Work records from USAID DEC catalog references."""

    def __init__(
        self,
        base_url: str = DEFAULT_CATALOG_URL,
        *,
        engine: DownloadEngine | None = None,
        cache_dir: Path | None = None,
    ):
        del base_url, engine, cache_dir

    def fetch(self, refs: Iterable[WorkRef]) -> Iterator[Work]:
        for ref in refs:
            extra = dict(ref.extra)
            pdf_url = extra.get("pdf_url")
            formats = (
                [Format(name="pdf", media_type="application/pdf", url=pdf_url)]
                if isinstance(pdf_url, str) and pdf_url
                else []
            )
            authors = extra.get("authors") or []
            if not isinstance(authors, list):
                authors = []
            subjects = extra.get("subjects") or []
            geographies = extra.get("geographies") or []
            work = Work(
                id=ref.id,
                source=USAIDDEC_SOURCE,
                title=str(extra.get("title") or ref.id),
                creators=_author_creators([str(a) for a in authors]),
                languages=[
                    str(lang) for lang in (extra.get("languages") or ["en"]) if lang
                ],
                license="With permission from AidData",
                formats=formats,
                collections=_collections(
                    (str(extra["class_name"]) if extra.get("class_name") else None),
                    [str(s) for s in subjects if s],
                ),
                description=(
                    str(extra["description"]) if extra.get("description") else None
                ),
                published=(
                    str(extra["date_published"])
                    if extra.get("date_published")
                    else None
                ),
                source_url=(
                    str(extra["source_url"]) if extra.get("source_url") else None
                ),
                extra={
                    "bibtype": extra.get("bibtype"),
                    "file_size": extra.get("file_size"),
                    "subjects": subjects,
                    "geographies": geographies,
                },
            )
            yield work
