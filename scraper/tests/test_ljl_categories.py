import pytest

from papers2zim.sources.litteraturejeunesselibre.categories import (
    LJL_CATEGORIES,
    category_resolver,
)


@pytest.mark.parametrize(
    ("categories", "expected"),
    [
        (("chien",), ["Animaux"]),
        (("conte",), ["Contes & légendes"]),
        (("nature", "jardin"), ["Nature & environnement"]),
        (("sorcière", "dragon"), ["Fantastique & magie"]),
        (("chevalier", "roi"), ["Histoire & civilisations"]),
        (("avion", "train"), ["Voyages & transports"]),
        (("noel", "pâques"), ["Fêtes & traditions"]),
    ],
)
def test_collapses_tags_into_broad_collections(categories, expected):
    assert category_resolver.collections_for(categories) == expected


@pytest.mark.parametrize(
    ("categories", "expected"),
    [
        (
            "chien, conte, nature",
            ["Animaux", "Nature & environnement", "Contes & légendes"],
        ),
        ("sorcière, chien", ["Animaux", "Fantastique & magie"]),
    ],
)
def test_splits_comma_joined_tags(categories, expected):
    assert category_resolver.collections_for([categories]) == expected


def test_collections_are_ordered_by_priority():
    assert category_resolver.collections_for(["conte", "chien"]) == [
        "Animaux",
        "Contes & légendes",
    ]


def test_deduplicates_repeated_tags():
    assert category_resolver.collections_for(["chien", "chien"]) == ["Animaux"]


def test_unknown_tags_fall_back_to_autres():
    assert category_resolver.collections_for(["Pas une catégorie LJL"]) == [
        category_resolver.fallback
    ]


def test_known_and_unknown_tags_are_both_kept():
    assert category_resolver.collections_for(["chien, Nouvelle catégorie"]) == [
        "Animaux",
        category_resolver.fallback,
    ]


def test_blank_parts_do_not_fall_back_to_autres():
    assert category_resolver.collections_for(["chien, ", ""]) == ["Animaux"]


def test_every_advertised_tag_belongs_to_a_known_collection():
    for category in LJL_CATEGORIES:
        assert category_resolver.collections_for([category]) != [
            category_resolver.fallback
        ]
