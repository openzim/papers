"""Tests for validate_i18n."""

from papers2zim.scripts.validate_i18n import (
    extract_placeholders,
    get_ignored_keys,
    get_leaf_keys,
    get_leaf_values,
    validate_metadata_defaults_lengths,
    validate_plural_messages,
)


def _en_data(**overrides):
    data = {"about": {}}
    data.update(overrides)
    return data


def test_ignores_locale_metadata_fields():
    assert {"language", "isocode"} <= get_ignored_keys(_en_data())


def test_ignores_collection_ids_found_in_data():
    ignored = get_ignored_keys({"collections": {"a": {}, "18": {}}})
    assert {"collections.a", "collections.18"} <= ignored


def test_ignores_intro_and_mission_paragraph_keys():
    data = _en_data(
        about={
            "introHeading": "Introduction",
            "introParagraph1": "One",
            "introParagraph2": "Two",
            "missionHeading": "Mission",
            "missionParagraph1": "One",
        }
    )
    ignored = get_ignored_keys(data)
    assert {
        "about.introParagraph1",
        "about.introParagraph2",
        "about.missionParagraph1",
    } <= ignored


def test_ignores_arbitrarily_high_paragraph_numbers():
    data = _en_data(
        about={
            "introParagraph1": "One",
            "missionParagraph23": "Twenty-three",
            "missionParagraph999": "Nine ninety-nine",
        }
    )
    ignored = get_ignored_keys(data)
    assert "about.missionParagraph23" in ignored
    assert "about.missionParagraph999" in ignored


def test_does_not_ignore_other_about_keys():
    data = _en_data(
        about={
            "attribution": "Attribution",
            "introHeading": "Introduction",
            "missionAuthor": "Author",
            "missionHeading": "Mission",
        }
    )
    ignored = get_ignored_keys(data)
    assert not any(key.startswith("about.") for key in ignored)


def test_ignores_no_paragraph_keys_without_an_about_section():
    assert not any(key.startswith("about.") for key in get_ignored_keys({}))


def test_tolerates_non_dict_about_section():
    ignored = get_ignored_keys({"about": ["not", "a", "mapping"]})
    assert not any(key.startswith("about.") for key in ignored)


def test_does_not_match_partial_paragraph_names():
    data = _en_data(
        about={
            "introParagraph1a": "Trailing letter",
            "missionParagraphX": "Wrong suffix",
            "paragraph1": "No section prefix",
        }
    )
    ignored = get_ignored_keys(data)
    assert not any(key.startswith("about.") for key in ignored)


def test_plural_message_is_a_single_leaf_key():
    data = {"zimInfo": {"books": {"one": "Book", "other": "Books"}, "title": "T"}}
    assert get_leaf_keys(data) == {"zimInfo.books", "zimInfo.title"}


def test_plural_message_value_joins_forms_for_placeholder_checks():
    data = {"books": {"one": "One book", "other": "{count} books"}}
    values = get_leaf_values(data)
    assert set(values) == {"books"}
    assert extract_placeholders(values["books"]) == {"count"}


def test_valid_plural_messages_have_no_issue():
    data = {
        "a": {"books": {"one": "Book", "other": "Books"}},
        "b": {"zero": "None", "two": "Two", "few": "F", "many": "M", "other": "O"},
    }
    assert validate_plural_messages(data) == []


def test_plural_message_without_other_form_is_reported():
    issues = validate_plural_messages({"a": {"books": {"one": "Book"}}})
    assert len(issues) == 1
    assert "a.books" in issues[0]
    assert "'other'" in issues[0]


def test_plural_message_with_invalid_category_is_reported():
    issues = validate_plural_messages({"books": {"one": "Book", "plural": "Books"}})
    assert len(issues) == 1
    assert "['plural']" in issues[0]


def test_namespace_without_plural_categories_is_not_a_plural_message():
    data = {"common": {"title": "T", "nested": {"label": "L"}}}
    assert validate_plural_messages(data) == []
    assert get_leaf_keys(data) == {"common.title", "common.nested.label"}


def test_metadata_defaults_within_length_have_no_issue():
    data = {
        "gutenberg": {
            "metadata_defaults": {
                "title": "Project Gutenberg Library",
                "description": "All books from Project Gutenberg",
            }
        }
    }
    assert validate_metadata_defaults_lengths(data) == []


def test_overlong_title_default_is_reported():
    data = {
        "gutenberg": {"metadata_defaults": {"title": "A" * 31}},
    }
    issues = validate_metadata_defaults_lengths(data)
    assert len(issues) == 1
    assert "gutenberg.metadata_defaults.title" in issues[0]


def test_overlong_description_default_is_reported():
    data = {
        "opentextbooks": {"metadata_defaults": {"description": "A" * 81}},
    }
    issues = validate_metadata_defaults_lengths(data)
    assert len(issues) == 1
    assert "opentextbooks.metadata_defaults.description" in issues[0]


def test_metadata_defaults_ignores_non_string_and_missing_values():
    data = {
        "common": {"not_metadata": "x"},
        "gutenberg": {"metadata_defaults": {"title": 123}},
        "wikisource": "not-a-dict",
    }
    assert validate_metadata_defaults_lengths(data) == []
