"""Tests for the shared category-to-collection resolver."""

# ruff: noqa: RUF001

import pytest

from papers2zim.core.categories import (
    FALLBACK_COLLECTION,
    CategoryResolver,
    normalize_category,
)


@pytest.fixture
def resolver() -> CategoryResolver:
    return CategoryResolver(
        {
            "Animals": ("dog", "cat"),
            "Tales": ("tale", "legend"),
            "Other stories": ("story",),
        },
        ignored=("21st century", "French literature"),
    )


def test_normalize_category_collapses_case_whitespace_and_punctuation():
    assert normalize_category("  French   Literature. ") == "french literature"
    assert normalize_category("Littérature d’Oc") == "littérature d'oc"
    assert normalize_category("Science–Fiction") == "science-fiction"


def test_order_appends_the_fallback_collection(resolver):
    assert resolver.order == (
        "Animals",
        "Tales",
        "Other stories",
        FALLBACK_COLLECTION,
    )


def test_collections_for_maps_tags_and_keeps_the_declaration_order(resolver):
    assert resolver.collections_for(["tale", "dog"]) == ["Animals", "Tales"]


def test_collections_for_splits_comma_joined_tags(resolver):
    assert resolver.collections_for(["dog, tale", "cat"]) == ["Animals", "Tales"]


def test_collections_for_drops_ignored_facets(resolver):
    assert resolver.collections_for(["21st century", "French literature"]) == []
    assert resolver.collections_for(["dog", "21st century"]) == ["Animals"]


def test_collections_for_falls_back_for_unknown_tags(resolver):
    assert resolver.collections_for(["unknown"]) == [FALLBACK_COLLECTION]


def test_collections_for_ignores_blank_and_non_string_values(resolver):
    assert resolver.collections_for(["", "  ", 42, None]) == []  # type: ignore[list-item]


def test_collections_for_deduplicates_and_drops_blank_parts(resolver):
    assert resolver.collections_for(["dog", "dog, "]) == ["Animals"]


def test_custom_fallback_replaces_the_default():
    resolver = CategoryResolver({"Animals": ("dog",)})

    assert resolver.fallback == FALLBACK_COLLECTION
    assert resolver.collections_for(["unknown"]) == [FALLBACK_COLLECTION]

    custom = CategoryResolver({"Animals": ("dog",)}, fallback="Misc")
    assert custom.order == ("Animals", "Misc")
    assert custom.collections_for(["unknown"]) == ["Misc"]


def test_exposes_its_declared_tags_and_normalized_mapping(resolver):
    assert resolver.category_names == ("dog", "cat", "tale", "legend", "story")
    assert resolver.category_collections["cat"] == "Animals"
    assert resolver.ignored == frozenset({"21st century", "french literature"})

    mapping = resolver.category_collections
    mapping["cat"] = "Tales"
    assert resolver.category_collections["cat"] == "Animals"
