"""Regression checks for Zimfarm recipe options."""

import json
from pathlib import Path

DEFINITION_PATH = Path(__file__).parents[2] / "offliner-definition.json"


def test_recipe_defines_supported_sources_and_source_specific_filters():
    definition = json.loads(DEFINITION_PATH.read_text(encoding="utf-8"))
    flags = definition["flags"]

    assert flags["source"] == {
        "type": "string-enum",
        "required": False,
        "title": "Source",
        "description": (
            "Book source to scrape. Source-specific options are shown below; do not "
            "combine options from different sources."
        ),
        "choices": [
            {
                "title": "Bibliothèque numérique romande",
                "value": "bibliothequenumeriqueromande",
                "dependents": [
                    "bnr_series",
                    "bnr_authors",
                    "bnr_categories",
                    "bnr_titles",
                    "bnr_ids",
                ],
            },
            {
                "title": "Project Gutenberg",
                "value": "gutenberg",
                "dependents": [
                    "lcc_shelves",
                    "with_author_bio",
                    "with_author_portrait",
                ],
            },
            {
                "title": "Littérature jeunesse libre",
                "value": "litteraturejeunesselibre",
                "dependents": [
                    "ljl_series",
                    "ljl_authors",
                    "ljl_categories",
                    "ljl_titles",
                    "ljl_ids",
                ],
            },
            {
                "title": "One More Library",
                "value": "onemorelibrary",
                "dependents": ["categories", "oml_ids"],
            },
            {
                "title": "Open Textbook Library",
                "value": "opentextbooks",
                "dependents": ["subjects", "otl_ids"],
            },
            {
                "title": "Wikisource",
                "value": "wikisource",
                "dependents": ["wikisource_pages"],
            },
            {
                "title": "USAID DEC Archive",
                "value": "usaiddec",
                "dependents": ["usaid_ids"],
            },
        ],
    }
    assert {
        "lcc_shelves",
        "categories",
        "oml_ids",
        "subjects",
        "otl_ids",
        "wikisource_pages",
        "usaid_ids",
        "with_author_bio",
        "with_author_portrait",
        "bnr_series",
        "bnr_authors",
        "bnr_categories",
        "bnr_titles",
        "bnr_ids",
        "ljl_series",
        "ljl_authors",
        "ljl_categories",
        "ljl_titles",
        "ljl_ids",
    }.issubset(flags)


def test_bnr_filter_flags_are_bnr_only_dependents():
    definition = json.loads(DEFINITION_PATH.read_text(encoding="utf-8"))
    flags = definition["flags"]
    bnr_flags = {
        "bnr_series",
        "bnr_authors",
        "bnr_categories",
        "bnr_titles",
        "bnr_ids",
    }

    assert bnr_flags.issubset(flags)
    for name in bnr_flags:
        assert flags[name]["required"] is False

    bnr_choices = [
        choice
        for choice in flags["source"]["choices"]
        if choice["value"] == "bibliothequenumeriqueromande"
    ]
    assert len(bnr_choices) == 1
    assert bnr_flags.issubset(bnr_choices[0]["dependents"])

    for choice in flags["source"]["choices"]:
        if choice["value"] != "bibliothequenumeriqueromande":
            assert bnr_flags.isdisjoint(choice["dependents"])


def test_ljl_filter_flags_are_ljl_only_dependents():
    definition = json.loads(DEFINITION_PATH.read_text(encoding="utf-8"))
    flags = definition["flags"]
    ljl_flags = {
        "ljl_series",
        "ljl_authors",
        "ljl_categories",
        "ljl_titles",
        "ljl_ids",
    }

    assert ljl_flags.issubset(flags)
    for name in ljl_flags:
        assert flags[name]["required"] is False

    ljl_choices = [
        choice
        for choice in flags["source"]["choices"]
        if choice["value"] == "litteraturejeunesselibre"
    ]
    assert len(ljl_choices) == 1
    assert ljl_flags.issubset(ljl_choices[0]["dependents"])

    for choice in flags["source"]["choices"]:
        if choice["value"] != "litteraturejeunesselibre":
            assert ljl_flags.isdisjoint(choice["dependents"])

    assert definition["modelValidators"] == [
        {
            "name": "check_exclusive_fields",
            "fields": [
                "bnr_series",
                "bnr_authors",
                "bnr_categories",
                "bnr_titles",
                "ljl_series",
                "ljl_authors",
                "ljl_categories",
                "ljl_titles",
            ],
        }
    ]


def test_recipe_uses_enum_choices_for_supported_formats():
    definition = json.loads(DEFINITION_PATH.read_text(encoding="utf-8"))

    assert definition["flags"]["formats"]["type"] == "list-of-string-enum"
    assert [
        choice["value"] for choice in definition["flags"]["formats"]["choices"]
    ] == ["epub", "html", "pdf"]


def test_recipe_exposes_custom_zim_tags():
    definition = json.loads(DEFINITION_PATH.read_text(encoding="utf-8"))

    assert definition["flags"]["zim_tags"] == {
        "type": "string",
        "required": False,
        "title": "ZIM Tags",
        "description": (
            "Semicolon-separated ZIM tags. Overrides the selected source's default "
            "tags; for example: _category:medical;gutenberg."
        ),
    }
    assert {"metadata": "Tags", "flag": "zim_tags"} in definition["zimMetadata"]


def test_with_author_bio_and_portrait_are_pg_only_boolean_flags():
    definition = json.loads(DEFINITION_PATH.read_text(encoding="utf-8"))
    flags = definition["flags"]

    assert flags["with_author_bio"] == {
        "type": "boolean",
        "required": False,
        "title": "With author biography",
        "description": (
            "Add author biography fetched from the English Wikipedia. "
            "Project Gutenberg source only for now."
        ),
    }
    assert flags["with_author_portrait"] == {
        "type": "boolean",
        "required": False,
        "title": "With author portrait",
        "description": (
            "Add author portrait fetched from the English Wikipedia. "
            "Project Gutenberg source only for now."
        ),
    }

    gutenberg_choices = [
        choice
        for choice in flags["source"]["choices"]
        if choice["value"] == "gutenberg"
    ]
    assert "with_author_bio" in gutenberg_choices[0]["dependents"]
    assert "with_author_portrait" in gutenberg_choices[0]["dependents"]
    for choice in flags["source"]["choices"]:
        if choice["value"] != "gutenberg":
            assert "with_author_bio" not in choice["dependents"]
            assert "with_author_portrait" not in choice["dependents"]


def test_recipe_exposes_optimization_cache():
    definition = json.loads(DEFINITION_PATH.read_text(encoding="utf-8"))

    assert definition["flags"]["optimization_cache"] == {
        "type": "url",
        "required": False,
        "title": "Optimization Cache URL",
        "description": "URL with credentials and bucket name to S3 Optimization Cache",
        "secret": True,
    }


def test_recipe_exposes_index_format_as_an_optional_enum():
    definition = json.loads(DEFINITION_PATH.read_text(encoding="utf-8"))
    index_format = definition["flags"]["index_format"]

    assert index_format["type"] == "string-enum"
    assert index_format["required"] is False
    assert [choice["value"] for choice in index_format["choices"]] == [
        "epub",
        "html",
        "pdf",
    ]
