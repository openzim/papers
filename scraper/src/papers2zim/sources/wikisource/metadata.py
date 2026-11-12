"""Wikisource metadata access.

The OPDS feed entries parsed by `sources.wikisource.catalog` already carry every
field the pipeline needs, including the per-format ws-export download links, so
this port only maps a `WorkRef` into a `Work` - there is no per-book fetch.
"""

from collections.abc import Iterable, Iterator

from papers2zim.core.models import Creator, Format, Work
from papers2zim.core.ports import MetadataPort, WorkRef
from papers2zim.core.utils import author_id
from papers2zim.sources.wikisource.catalog import WIKISOURCE_SOURCE


class WikisourceMetadata(MetadataPort):
    """Maps discovered `WorkRef`s into `Work`s using the parsed feed data."""

    def fetch(self, refs: Iterable[WorkRef]) -> Iterator[Work]:
        for ref in refs:
            yield self._to_work(ref)

    @staticmethod
    def _to_work(ref: WorkRef) -> Work:
        extra = ref.extra
        author = extra.get("author")
        creators = (
            [Creator(id=author_id(author), display_name=author, sort_name=author)]
            if author
            else []
        )
        language = extra.get("language")
        return Work(
            id=ref.id,
            source=WIKISOURCE_SOURCE,
            title=extra.get("title") or "Untitled",
            creators=creators,
            languages=[language] if language else [],
            license=extra.get("license"),
            formats=[
                Format(name=name, media_type=media_type, url=url)
                for name, media_type, url in extra.get("formats", [])
            ],
            source_url=extra.get("source_url"),
            published=extra.get("issued"),
            extra={
                "wikisource_page": extra.get("page"),
                "wikisource_lang": extra.get("lang"),
            },
        )
