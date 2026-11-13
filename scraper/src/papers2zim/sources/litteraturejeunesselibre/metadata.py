"""Littérature jeunesse libre book metadata.

The OPDS entries parsed by `sources.litteraturejeunesselibre.catalog` already
carry every field the pipeline needs, including the EPUB and PDF download links,
so this port only maps a `WorkRef` into a `Work` - there is no per-book fetch.
"""

from collections.abc import Iterable, Iterator
from typing import Any

from papers2zim.core.models import CollectionRef, Cover, Creator, Format, Work
from papers2zim.core.ports import MetadataPort, WorkRef
from papers2zim.core.utils import author_id, slug_id
from papers2zim.sources.litteraturejeunesselibre.catalog import (
    LJL_SOURCE,
    normalize_language,
)

# LJL publishes French-language children's books; fall back to French when an
# entry does not advertise a language.
DEFAULT_LANGUAGE = "fr"


class LitteratureJeunesseLibreMetadata(MetadataPort):
    """Maps discovered `WorkRef`s into `Work`s using the parsed feed data."""

    def fetch(self, refs: Iterable[WorkRef]) -> Iterator[Work]:
        for ref in refs:
            yield self._to_work(ref)

    @staticmethod
    def _to_work(ref: WorkRef) -> Work:
        extra = ref.extra
        formats = _formats_from_extra(extra)
        creators = [
            Creator(id=author_id(name), display_name=name, sort_name=name)
            for name in _texts(extra.get("authors"))
        ]
        cover_url = extra.get("cover_url")
        return Work(
            id=ref.id,
            source=LJL_SOURCE,
            title=extra.get("title") or "Untitled",
            creators=creators,
            languages=_languages(extra.get("languages")),
            formats=formats,
            cover=Cover(source_url=cover_url) if cover_url else None,
            collections=[
                CollectionRef(id=slug_id(name), name=name, kind="category")
                for name in _texts(extra.get("categories"))
            ],
            description=extra.get("description"),
            source_url=next((fmt.url for fmt in formats if fmt.url), None),
        )


def _texts(values: Any) -> list[str]:
    """Non-empty strings from a feed-provided list."""
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str) and value.strip()]


def _languages(values: Any) -> list[str]:
    """Normalized language codes, defaulting to French when none is advertised."""
    languages: list[str] = []
    for value in _texts(values):
        if (language := normalize_language(value)) and language not in languages:
            languages.append(language)
    return languages or [DEFAULT_LANGUAGE]


def _formats_from_extra(extra: dict[str, Any]) -> list[Format]:
    """Work formats, accepting either `Format` objects or their serialized form."""
    formats: list[Format] = []
    for value in extra.get("formats") or []:
        if isinstance(value, Format):
            formats.append(value)
        elif isinstance(value, dict):
            formats.append(Format(**value))
    return formats
