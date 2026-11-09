"""Bibliothèque numérique romande book metadata.

The OPDS entries parsed by `sources.bibliothequenumeriqueromande.catalog` already
carry every field the pipeline needs, including the EPUB download link, so this
port only maps a `WorkRef` into a `Work` - there is no per-book fetch.
"""

from collections.abc import Iterable, Iterator

from papers2zim.core.models import CollectionRef, Cover, Creator, Format, Work
from papers2zim.core.ports import MetadataPort, WorkRef
from papers2zim.core.utils import author_id, slug_id
from papers2zim.sources.bibliothequenumeriqueromande.catalog import (
    BNR_LANGUAGE,
    BNR_SOURCE,
    EPUB_MEDIA_TYPE,
)


class BibliothequeNumeriqueRomandeMetadata(MetadataPort):
    """Maps discovered `WorkRef`s into `Work`s using the parsed feed data."""

    def fetch(self, refs: Iterable[WorkRef]) -> Iterator[Work]:
        for ref in refs:
            yield self._to_work(ref)

    @staticmethod
    def _to_work(ref: WorkRef) -> Work:
        extra = ref.extra
        author = extra.get("author")
        source_url = extra.get("source_url")
        cover_url = extra.get("cover_url")
        creators = (
            [
                Creator(
                    id=author_id(author),
                    display_name=author,
                    sort_name=author,
                )
            ]
            if isinstance(author, str) and author
            else []
        )
        return Work(
            id=ref.id,
            source=BNR_SOURCE,
            title=extra.get("title") or "Untitled",
            creators=creators,
            languages=[BNR_LANGUAGE],
            formats=(
                [Format(name="epub", media_type=EPUB_MEDIA_TYPE, url=source_url)]
                if source_url
                else []
            ),
            cover=Cover(source_url=cover_url) if cover_url else None,
            collections=[
                CollectionRef(
                    id=slug_id(category), name=category, kind="category"
                )
                for category in extra.get("categories") or []
                if isinstance(category, str) and category
            ],
            description=extra.get("description"),
            source_url=source_url,
        )
