"""Readable, unique slugs for the locations readers navigate and share.

Works and creators keep their source ids internally (deduplication, source
links); slugs are derived once at export time so the Vue routes, the JSON
detail files, the search entries and the No-JS pages all agree on one
readable name per entity.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from papers2zim.core.models import Work
from papers2zim.core.utils import slugify, work_creators


@dataclass(frozen=True, slots=True)
class Slugs:
    """Slugs of every work and creator, keyed by their internal id"""

    works: dict[str, str]
    authors: dict[str, str]


def _unique_slugs(
    names: Sequence[tuple[str, str]],
    fallback: str,
    reserved_ids: frozenset[str] = frozenset(),
) -> dict[str, str]:
    """Assign one unique slug per id, suffixing later holders of a taken slug.

    Every natural slug is reserved before anything is assigned, so a generated
    `-1` suffix can never take the slug a differently named entity would get on
    its own. Entities without a usable slug (emoji-only titles) get the type
    name and the same counter. `reserved_ids` are the source ids the other
    works still address their own detail file with; an entity may keep its own.
    """
    reserved = {slug for _, slug in names if slug}
    assigned: dict[str, str] = {}
    used: set[str] = set()
    for entity_id, slug in names:
        base = slug or fallback
        candidate = base
        counter = 1
        while (
            candidate in used
            or (candidate != slug and candidate in reserved)
            or (candidate != entity_id and candidate in reserved_ids)
        ):
            candidate = f"{base}-{counter}"
            counter += 1
        assigned[entity_id] = candidate
        used.add(candidate)
    return assigned


def build_slugs(works: Sequence[Work]) -> Slugs:
    """Slug every work and creator of the catalog, in a stable id order.

    Slugs are assigned over the whole catalog before anything is written, and
    the order is derived from the ids rather than the work-store insertion
    order, so parallel processing cannot make suffixes move between runs.
    """
    ordered = sorted(works, key=lambda work: work.id)
    work_names = [(work.id, slugify(work.title)) for work in ordered]
    author_names: list[tuple[str, str]] = []
    seen: set[str] = set()
    for work in ordered:
        for creator in work_creators(work):
            if creator.id not in seen:
                seen.add(creator.id)
                author_names.append((creator.id, slugify(creator.display_name)))
    author_names.sort()
    work_ids = frozenset(work.id for work in ordered)
    return Slugs(
        works=_unique_slugs(work_names, "book", work_ids),
        authors=_unique_slugs(author_names, "author"),
    )
