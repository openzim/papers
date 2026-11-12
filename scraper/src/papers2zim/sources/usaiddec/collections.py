"""Curated thematic collections for the USAID DEC Archive.

AidData tags each evaluation report with a free-text ``Class`` label drawn
from a few hundred sector names, and with a long list of thesaurus
descriptors. Exposing those labels directly would create well over a
thousand near-duplicate collections ("HIV/AIDS" and "HIV / AIDS", "Health"
and "Health care", ...), which is unusable in the UI.

Instead, this module folds every report into a small curated set of thematic
sectors (about twenty). The rules are ordered: the first matching keyword
wins, so more specific sectors such as HIV/AIDS are checked before the
generic Health sector.
"""

from collections.abc import Iterable

OTHER_COLLECTION = "Other"

# Ordered (collection name, keywords). Keywords are matched against the
# lowercased report class, then against its thesaurus descriptors.
COLLECTION_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("HIV/AIDS", ("hiv",)),
    (
        "Maternal & Child Health",
        (
            "maternal",
            "child survival",
            "child health",
            "child nutrition",
            "breastfeeding",
            "infant",
            "family health",
        ),
    ),
    (
        "Reproductive Health & Family Planning",
        ("reproductive", "family planning", "contracept"),
    ),
    ("Nutrition", ("nutrition",)),
    (
        "Health",
        (
            "health",
            "disease",
            "tuberculosis",
            "malaria",
            "immunization",
            "medical",
            "hospital",
            "clinic",
            "epidemic",
            "pandemic",
        ),
    ),
    ("Water & Sanitation", ("water", "sanitation", "hydrology", "potable")),
    (
        "Agriculture & Food Security",
        (
            "agricultur",
            "food security",
            "food aid",
            "agribusiness",
            "crop",
            "livestock",
            "fisher",
            "aquaculture",
            "irrigation",
            "farming",
            "fertilizer",
            "seed",
            "maize",
            "food processing",
            "food supply",
            "cooperative",
            "rural development",
            "animal husbandry",
        ),
    ),
    (
        "Environment & Climate",
        (
            "environment",
            "natural resources",
            "biological diversity",
            "ecology",
            "forestry",
            "climate",
            "pollution",
            "conservation",
            "wildlife",
            "soil",
            "coastal",
        ),
    ),
    (
        "Education",
        ("education", "school", "teacher", "literacy", "learning", "vocational"),
    ),
    (
        "Energy & Infrastructure",
        (
            "energy",
            "electric",
            "power",
            "renewable",
            "road",
            "transport",
            "housing",
            "infrastructure",
            "construction",
            "urban",
            "steel",
        ),
    ),
    (
        "Technology & Communications",
        (
            "technology",
            "information",
            "communication",
            "media",
            "science",
            "data collection",
        ),
    ),
    (
        "Economic Growth & Trade",
        (
            "economic",
            "trade",
            "financ",
            "investment",
            "credit",
            "market",
            "business",
            "enterprise",
            "employment",
            "industry",
            "exports",
            "income",
            "private sector",
            "capital",
            "privatization",
            "banking",
            "labor",
        ),
    ),
    (
        "Governance & Public Administration",
        (
            "governance",
            "government",
            "public administration",
            "budget",
            "management reform",
            "legislative",
            "laws and legislation",
            "rule of law",
            "public land",
            "demobilization",
            "land reform",
            "development cooperation",
            "development assistance",
            "foreign assistance",
            "international politics",
            "embargoes",
        ),
    ),
    (
        "Democracy & Civil Society",
        (
            "civil society",
            "democrat",
            "election",
            "human rights",
            "social justice",
            "political",
            "advocacy",
            "organizations",
        ),
    ),
    (
        "Conflict & Security",
        (
            "conflict",
            "security",
            "displaced",
            "land mines",
            "emergency",
            "transition",
            "resilient societies",
        ),
    ),
    (
        "Humanitarian Assistance & Disaster",
        ("disaster", "humanitarian", "relief", "refugee"),
    ),
    ("Gender Equality", ("gender", "women", "girls")),
    (
        "Poverty & Social Development",
        (
            "poverty",
            "social",
            "communit",
            "quality of life",
            "population groups",
            "regional",
            "socioeconomic",
            "human behavior",
            "psychology",
            "culture and society",
            "safety",
        ),
    ),
    (
        "Population & Demography",
        ("population", "demograph", "vital statistics", "migration"),
    ),
    (
        "Capacity Building & Evaluation",
        (
            "training",
            "capacity",
            "evaluation",
            "performance",
            "planning",
            "management",
            "administration",
            "personnel",
            "research",
            "strategic",
        ),
    ),
)

COLLECTION_NAMES: tuple[str, ...] = (
    *(name for name, _ in COLLECTION_RULES),
    OTHER_COLLECTION,
)


def normalize_class(value: str | None) -> str:
    """Normalize a dataset ``Class`` value into a keyword-matching haystack.

    A few values are full paths ("Top/Health/Diseases/Tuberculosis"); the
    leaf is the meaningful part. Labels such as "HIV / AIDS" keep their
    spaces around the slash and are left intact.
    """
    text = (value or "").strip()
    if not text:
        return ""
    if text.casefold().startswith("top/"):
        text = text[len("top/") :].split("/")[-1]
    return text.casefold()


def _match(haystack: str) -> str | None:
    for name, keywords in COLLECTION_RULES:
        if any(keyword in haystack for keyword in keywords):
            return name
    return None


def collection_for(class_name: str | None, subjects: Iterable[str] = ()) -> str:
    """Return the curated collection a report belongs to."""
    matched = _match(normalize_class(class_name))
    if matched:
        return matched
    subject_text = " | ".join(
        subject.casefold() for subject in subjects if subject and subject.strip()
    )
    matched = _match(subject_text)
    if matched:
        return matched
    return OTHER_COLLECTION


def collection_slug(name: str) -> str:
    """Build a stable, URL-friendly collection id from its display name."""
    slug = name.casefold().replace("&", " and ")
    slug = "".join(character if character.isalnum() else "-" for character in slug)
    return "-".join(part for part in slug.split("-") if part)
