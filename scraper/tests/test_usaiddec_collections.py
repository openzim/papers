"""Tests for the curated USAID DEC Archive collections."""

import pytest

from papers2zim.sources.usaiddec.collections import (
    COLLECTION_NAMES,
    OTHER_COLLECTION,
    collection_for,
    collection_slug,
    normalize_class,
)


@pytest.mark.parametrize(
    ("class_name", "expected"),
    (
        ("HIV / AIDS", "HIV/AIDS"),
        ("Maternal child health care", "Maternal & Child Health"),
        ("Reproductive health care", "Reproductive Health & Family Planning"),
        ("Nutrition", "Nutrition"),
        ("Health (General)", "Health"),
        ("Water supply and sanitation", "Water & Sanitation"),
        ("Food security", "Agriculture & Food Security"),
        ("Climate change", "Environment & Climate"),
        ("Basic education", "Education"),
        ("Energy technology", "Energy & Infrastructure"),
        (
            "Information management, systems and equipment",
            "Technology & Communications",
        ),
        ("Economic growth and development", "Economic Growth & Trade"),
        ("Rule of law", "Governance & Public Administration"),
        ("Human rights and social justice", "Democracy & Civil Society"),
        ("Conflict prevention", "Conflict & Security"),
        ("Disaster relief and response", "Humanitarian Assistance & Disaster"),
        ("Gender based violence", "Gender Equality"),
        ("Poverty reduction", "Poverty & Social Development"),
        ("Population surveys", "Population & Demography"),
        ("Performance measurement", "Capacity Building & Evaluation"),
    ),
)
def test_collection_for_maps_classes_to_curated_sectors(class_name, expected):
    assert collection_for(class_name) == expected


def test_collection_for_normalizes_top_level_paths():
    assert normalize_class("Top/Health/Diseases/Bacterial diseases/Tuberculosis") == (
        "tuberculosis"
    )
    assert collection_for("Top/Health/Diseases/Bacterial diseases/Tuberculosis") == (
        "Health"
    )


def test_collection_for_falls_back_to_thesaurus_subjects():
    assert collection_for(None, ["Education"]) == "Education"
    assert collection_for("", ["Food security"]) == "Agriculture & Food Security"


def test_collection_for_uses_other_when_nothing_matches():
    assert collection_for("Some unmapped label") == OTHER_COLLECTION
    assert collection_for(None, ["Unknown descriptor"]) == OTHER_COLLECTION


def test_curated_taxonomy_stays_in_the_expected_range():
    assert 18 <= len(COLLECTION_NAMES) <= 22
    assert len(set(COLLECTION_NAMES)) == len(COLLECTION_NAMES)


@pytest.mark.parametrize(
    ("name", "expected"),
    (
        ("Education", "education"),
        ("Agriculture & Food Security", "agriculture-and-food-security"),
        ("HIV/AIDS", "hiv-aids"),
        ("Other", "other"),
    ),
)
def test_collection_slug_is_url_friendly(name, expected):
    assert collection_slug(name) == expected
