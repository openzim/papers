"""USAID DEC Archive metadata access.

Catalog discovery already carries the dataset CSV metadata for each report,
so fetching a work is a direct conversion from the catalog reference.
"""

from collections.abc import Iterable, Iterator
from pathlib import Path

from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.models import CollectionRef, Creator, Format, Work
from papers2zim.core.ports import MetadataPort, WorkRef
from papers2zim.sources.usaiddec.catalog import DEFAULT_CATALOG_URL, USAIDDEC_SOURCE


def _author_creators(names: list[str]) -> list[Creator]:
    creators: list[Creator] = []
    for index, raw_name in enumerate(names, start=1):
        name = raw_name.strip()
        if not name:
            continue
        parts = name.split()
        sort_name = parts[-1] if parts else name
        creators.append(
            Creator(
                id=f"{USAIDDEC_SOURCE}-author-{index}-{abs(hash(name))}",
                display_name=name,
                sort_name=sort_name,
            )
        )
    return creators


def _collections(subjects: list[str], geographies: list[str]) -> list[CollectionRef]:
    refs: list[CollectionRef] = []
    seen: set[str] = set()
    for name in [*subjects[:3], *geographies[:1]]:
        key = name.casefold()
        if not name or key in seen:
            continue
        seen.add(key)
        refs.append(CollectionRef(id=f"subject:{key}", name=name, kind="subject"))
    return refs


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
                    [str(s) for s in subjects if s],
                    [str(g) for g in geographies if g],
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
