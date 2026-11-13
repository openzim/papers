"""Collapse flat source tags into a few broad browsing collections.

Sources such as Bibliothèque numérique romande and Littérature jeunesse libre
expose a flat, overlapping list of tags. Browsing that list is not practical,
so each source declares a mapping from its raw tags to the broad collections
used by the UI. `CategoryResolver` owns the normalization, lookup, ordering,
and fallback behavior; a source only provides the mapping data and the list of
tags that are facets rather than browsing collections.
"""

import unicodedata
from collections.abc import Iterable, Mapping

# Collection used for tags that are neither mapped nor explicit facets.
FALLBACK_COLLECTION = "Autres"

_CHARACTER_TRANSLATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u2013": "-",
        "\u2014": "-",
    }
)


def normalize_category(value: str) -> str:
    """Normalize a source tag for lookup."""
    text = unicodedata.normalize("NFKC", value).translate(_CHARACTER_TRANSLATION)
    return " ".join(text.split()).rstrip(" .").casefold()


class CategoryResolver:
    """Map a source's flat tags to broad, ordered browsing collections.

    ``collections`` maps each broad collection name to the source tags that
    belong to it. Its insertion order is the priority order used to pick a
    work's primary collection, so keep the most specific forms first.

    ``ignored`` lists tag facets (centuries, literary origins, ...) that must
    not fall back to the catch-all collection. Tags absent from both are mapped
    to ``fallback``.
    """

    def __init__(
        self,
        collections: Mapping[str, Iterable[str]],
        *,
        ignored: Iterable[str] = (),
        fallback: str = FALLBACK_COLLECTION,
    ):
        self._fallback = fallback
        self._order: tuple[str, ...] = (*collections, fallback)
        self._category_collections = {
            normalize_category(category): collection
            for collection, categories in collections.items()
            for category in categories
        }
        self._ignored = frozenset(normalize_category(category) for category in ignored)
        self._category_names: tuple[str, ...] = tuple(
            category for categories in collections.values() for category in categories
        )

    @property
    def order(self) -> tuple[str, ...]:
        """Broad collection names, in primary-collection priority order."""
        return self._order

    @property
    def fallback(self) -> str:
        """Collection used for tags that are neither mapped nor ignored."""
        return self._fallback

    @property
    def category_names(self) -> tuple[str, ...]:
        """Every raw tag mapped to a collection, in declaration order."""
        return self._category_names

    @property
    def category_collections(self) -> dict[str, str]:
        """Normalized tag to collection mapping."""
        return dict(self._category_collections)

    @property
    def ignored(self) -> frozenset[str]:
        """Normalized tags that are facets rather than browsing collections."""
        return self._ignored

    def collections_for(self, categories: Iterable[str]) -> list[str]:
        """Return the distinct collections for a work's source tags.

        Comma-joined tags are split so that, for example,
        ``"Roman, Société, Littérature anglo-saxonne, 19e"`` yields ``Roman``
        and ``Société``. Unrecognized tags fall back to `fallback`. The result
        is ordered by `order`, which makes the first item the work's primary
        collection.
        """
        found: set[str] = set()
        for category in categories:
            if not isinstance(category, str):
                continue
            for part in category.split(","):
                normalized = normalize_category(part)
                if not normalized or normalized in self._ignored:
                    continue
                found.add(self._category_collections.get(normalized, self._fallback))
        return [collection for collection in self._order if collection in found]
