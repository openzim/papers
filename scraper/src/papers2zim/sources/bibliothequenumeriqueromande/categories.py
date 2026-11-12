"""Collapse Bibliothèque numérique romande tags into a few broad collections.

BNR tags are a flat, overlapping list: a work typically carries a form
("Roman", "Conte"), a theme ("Société", "Amour"), an origin ("Littérature
anglo-saxonne"), and a century ("19e"), and some tags are comma-joined
combinations of all of these. Browsing that list is not practical, so this
module maps each tag to one of the broad collections used by the UI.

"""

import unicodedata
from collections.abc import Iterable

# Broad collection -> BNR tags that belong to it. The insertion order is the
# priority order used to pick a work's primary collection, so keep the most
# specific forms first and the catch-all "Roman" after other narrative genres
# but before themes.
_COLLECTIONS: dict[str, tuple[str, ...]] = {
    "Bande dessinée": ("Bande dessinée",),
    "Conte": ("Conte",),
    "Nouvelles": ("Nouvelles",),
    "Poésie": ("Poésie",),
    "Théâtre": ("Théâtre",),
    "Policier & Mystère": ("Policier-Mystère",),
    "Science-fiction & Fantastique": ("Fantastique-Science-Fiction-Anticipation",),
    "Aventure": ("Action & Aventure", "Aventures"),
    "Humour": ("Humour",),
    "Historique": ("Historique",),
    "Amour": ("Amour",),
    "Biographie & Autobiographie": ("Biographie-Autobiographie",),
    "Essai & Chronique": ("Essai et Chronique",),
    "Philosophie": ("Philosophie",),
    "Jeunesse": ("Littérature pour la jeunesse",),
    "Roman": (
        "Roman",
        "oman",
        "Fiction",
        "Écrits d'aujourd'hui",
        "Littérature populaire",
    ),
    "Art": ("Art",),
    "Société": ("Société", "Femmes", "Éducation", "Sport", "Animaux", "Érotisme"),
    "Voyage & Montagne": ("Récit de voyage", "Montagne"),
    "Régions & terroir": (
        "Littérature de terroir",
        "Ils ont écrit sur la Suisse",
        "Littérature suisse romande et des régions voisines",
        "Littérature suisse alémanique",
        "Littérature alémanique",
        "Littérature d'oc et de Rhône",
    ),
}

# Tags that are facets of a work rather than browsing collections: centuries and
# literary origins. They are listed explicitly so that they are not mistaken for
# a new, unmapped tag and sent to the fallback collection.
_IGNORED_CATEGORIES = (
    "16e",
    "17e",
    "18e",
    "19e",
    "20e",
    "21e",
    "Littérature anglo-saxonne",
    "Littérature anglophone",
    "Littérature arabe",
    "Littérature belge",
    "Littérature française",
    "Littérature française 19e",
    "Littérature hispanique",
    "Littérature hispanophone",
    "Littérature indienne",
    "Littérature italienne",
    "Littérature néerlandaise",
    "Littérature polonaise",
    "Littérature québécoise",
    "Littérature russe",
    "Littérature scandinave",
    "Littérature étrangère",
)

# Tags advertised by the BNR tag index, including facets and spelling variants.
# The test suite uses this list to check that every tag is either mapped to a
# collection or deliberately ignored.
BNR_CATEGORIES = (
    "16e",
    "17e",
    "18e",
    "19e",
    "19e.",
    "20e",
    "20e.",
    "21e",
    "Action & Aventure",
    "Amour",
    "Animaux",
    "Art",
    "Aventures",
    "Bande dessinée",
    "Biographie-Autobiographie",
    "Conte",
    "Essai et Chronique",
    "Fantastique-Science-Fiction-Anticipation",
    "Femmes",
    "Fiction",
    "Historique",
    "Humour",
    "Ils ont écrit sur la Suisse",
    "Littérature alémanique",
    "Littérature anglo-saxonne",
    "Littérature anglophone",
    "Littérature arabe",
    "Littérature belge",
    "Littérature d'oc et de Rhône",
    "Littérature d\u2019Oc et de Rhône",
    "Littérature de terroir",
    "Littérature étrangère",
    "Littérature française",
    "Littérature française 19e",
    "Littérature hispanique",
    "Littérature hispanophone",
    "Littérature indienne",
    "Littérature italienne",
    "Littérature néerlandaise",
    "Littérature polonaise",
    "Littérature populaire",
    "Littérature pour la jeunesse",
    "Littérature québécoise",
    "Littérature russe",
    "Littérature scandinave",
    "Littérature suisse alémanique",
    "Littérature suisse romande et des régions voisines",
    "Montagne",
    "Nouvelles",
    "oman",
    "Philosophie",
    "Policier-Mystère",
    "Poésie",
    "Roman",
    "Récit de voyage",
    "Société",
    "Sport",
    "Théâtre",
    "Écrits d'aujourd'hui",
    "Éducation",
    "Érotisme",
)

_CHARACTER_TRANSLATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u2013": "-",
        "\u2014": "-",
    }
)


def normalize_category(value: str) -> str:
    """Normalize a BNR tag for lookup."""
    text = unicodedata.normalize("NFKC", value).translate(_CHARACTER_TRANSLATION)
    return " ".join(text.split()).rstrip(" .").casefold()


def _build_category_collections() -> dict[str, str]:
    """Map every normalized tag to the collection it belongs to."""
    return {
        normalize_category(category): collection
        for collection, categories in _COLLECTIONS.items()
        for category in categories
    }


CATEGORY_COLLECTIONS = _build_category_collections()

IGNORED_CATEGORIES = frozenset(
    normalize_category(category) for category in _IGNORED_CATEGORIES
)

# Collection used for tags that are neither mapped nor explicit facets.
FALLBACK_COLLECTION = "Autres"

# Broad collection names, in primary-collection priority order.
COLLECTION_ORDER: tuple[str, ...] = (*_COLLECTIONS, FALLBACK_COLLECTION)


def collection_names_for_categories(categories: Iterable[str]) -> list[str]:
    """Return the distinct collections for a work's BNR tags.

    Comma-joined tags are split so that, for example,
    ``"Roman, Société, Littérature anglo-saxonne, 19e"`` yields ``Roman`` and
    ``Société``. Unrecognized tags fall back to `FALLBACK_COLLECTION`. The
    result is ordered by `COLLECTION_ORDER`, which makes the first item the
    work's primary collection.
    """
    found: set[str] = set()
    for category in categories:
        if not isinstance(category, str):
            continue
        for part in category.split(","):
            normalized = normalize_category(part)
            if not normalized or normalized in IGNORED_CATEGORIES:
                continue
            found.add(CATEGORY_COLLECTIONS.get(normalized, FALLBACK_COLLECTION))
    return [collection for collection in COLLECTION_ORDER if collection in found]
