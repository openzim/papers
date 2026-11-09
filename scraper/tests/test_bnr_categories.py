# ruff: noqa: RUF001
import pytest

from papers2zim.sources.bibliothequenumeriqueromande.categories import (
    FALLBACK_COLLECTION,
    collection_names_for_categories,
)


@pytest.mark.parametrize(
    ("categories", "expected"),
    [
        (
            ("17e", "Conte", "Littérature française"),
            ["Conte"],
        ),
        (("Action & Aventure",), ["Aventure"]),
        (("Aventures",), ["Aventure"]),
        (("oman",), ["Roman"]),
        (("Fiction",), ["Roman"]),
        (("Écrits d'aujourd'hui",), ["Roman"]),
        (("19e", "19e.", "20e", "20e."), []),
        (("Littérature anglo-saxonne", "Littérature belge"), []),
        (("Montagne", "Récit de voyage"), ["Voyage & Montagne"]),
    ],
)
def test_collapses_synonyms_and_drops_facets(categories, expected):
    assert collection_names_for_categories(categories) == expected


@pytest.mark.parametrize(
    ("categories", "expected"),
    [
        (
            (
                "Roman, Fantastique-Science-Fiction-Anticipation, Animaux, "
                "Littérature française, 20e"
            ),
            ["Science-fiction & Fantastique", "Roman", "Société"],
        ),
        ("Roman, Société, Littérature anglo-saxonne, 19e", ["Roman", "Société"]),
        (
            "Roman, Société, Littérature suisse romande et des régions voisines, 20e",
            ["Roman", "Société", "Régions & terroir"],
        ),
    ],
)
def test_splits_comma_joined_tags(categories, expected):
    assert collection_names_for_categories([categories]) == expected


def test_specific_genre_takes_priority_over_roman():
    assert collection_names_for_categories(["Roman", "Policier-Mystère"]) == [
        "Policier & Mystère",
        "Roman",
    ]


def test_deduplicates_variants_of_the_same_tag():
    assert collection_names_for_categories(
        ["Littérature d'oc et de Rhône", "Littérature d’Oc et de Rhône"]
    ) == ["Régions & terroir"]


def test_unknown_tags_fall_back_to_autres():
    assert collection_names_for_categories(["Pas une catégorie BNR"]) == [
        FALLBACK_COLLECTION
    ]


def test_known_and_unknown_tags_are_both_kept():
    assert collection_names_for_categories(["Roman, Nouvelle catégorie"]) == [
        "Roman",
        FALLBACK_COLLECTION,
    ]


def test_blank_parts_do_not_fall_back_to_autres():
    assert collection_names_for_categories(["Roman, ", ""]) == ["Roman"]
