"""Collapse Bibliothèque numérique romande tags into a few broad collections.

BNR tags are a flat, overlapping list: a work typically carries a form
("Roman", "Conte"), a theme ("Société", "Amour"), an origin ("Littérature
anglo-saxonne"), and a century ("19e"), and some tags are comma-joined
combinations of all of these. Browsing that list is not practical, so this
module maps each tag to one of the broad collections used by the UI.

"""

from papers2zim.core.categories import CategoryResolver

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

category_resolver = CategoryResolver(_COLLECTIONS, ignored=_IGNORED_CATEGORIES)
