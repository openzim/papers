"""Tests for Creative Commons license identifiers."""

import pytest

from papers2zim.core.licenses import license_identifier, license_label, license_url
from papers2zim.core.models import Work


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # Wikisource: the OPDS feed gives a URI
        ("http://creativecommons.org/licenses/by-sa/3.0", "CC-BY-SA-3.0"),
        ("https://creativecommons.org/licenses/by-sa/3.0/", "CC-BY-SA-3.0"),
        ("https://www.creativecommons.org/licenses/by/4.0/", "CC-BY-4.0"),
        ("https://creativecommons.org/licenses/by-sa/3.0/deed.en", "CC-BY-SA-3.0"),
        (
            "https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode",
            "CC-BY-NC-ND-4.0",
        ),
        ("https://creativecommons.org/licenses/by-nc/2.5/legalcode.fr", "CC-BY-NC-2.5"),
        ("https://creativecommons.org/publicdomain/zero/1.0/", "CC0-1.0"),
        ("http://creativecommons.org/publicdomain/zero/1.0/legalcode", "CC0-1.0"),
        # One More Library: short codes
        ("CC BY-SA 4.0", "CC-BY-SA-4.0"),
        ("cc by 4.0", "CC-BY-4.0"),
        ("CC BY-NC-ND 3.0", "CC-BY-NC-ND-3.0"),
        ("CC0", "CC0-1.0"),
        ("CC0 1.0", "CC0-1.0"),
        ("CC0 1.0 Universal", "CC0-1.0"),
        ("  CC BY-SA 4.0 ", "CC-BY-SA-4.0"),
        # Open Textbook Library: names without a version
        ("Attribution", "CC-BY"),
        ("Attribution-NonCommercial", "CC-BY-NC"),
        ("Attribution-NonCommercial-NoDerivs", "CC-BY-NC-ND"),
        ("Attribution-NonCommercial-ShareAlike", "CC-BY-NC-SA"),
        ("Attribution-NoDerivs", "CC-BY-ND"),
        ("Attribution-ShareAlike", "CC-BY-SA"),
        ("attribution-sharealike", "CC-BY-SA"),
        # An identifier is its own identifier
        ("CC-BY-SA-3.0", "CC-BY-SA-3.0"),
        ("CC-BY-NC-SA", "CC-BY-NC-SA"),
        ("CC0-1.0", "CC0-1.0"),
    ],
)
def test_license_identifier_recognizes_creative_commons(value, expected):
    assert license_identifier(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "   ",
        # Project Gutenberg's free text
        "Public domain in the USA.",
        "Copyrighted. Read the copyright notice inside this book for details.",
        # Other licenses the Open Textbook Library uses are not guessed at
        "No Rights Reserved",
        "Free Documentation License (GNU)",
        "Public domain",
        # Jurisdiction-specific ports are different licenses
        "http://creativecommons.org/licenses/by-sa/3.0/de/",
        "https://creativecommons.org/publicdomain/mark/1.0/",
        # Not Creative Commons, or not well formed
        "http://example.org/licenses/by-sa/3.0",
        "https://creativecommons.org/licenses/by-sa/3",
        "https://creativecommons.org/licenses/by-sa/3.0/de",
        "CC BY-ND-NC 4.0",
        "CC BY-SA 4.0 International",
        "CC",
    ],
)
def test_license_identifier_leaves_everything_else_alone(value):
    assert license_identifier(value) is None


def test_work_license_id_is_derived_from_license():
    assert (
        Work(
            id="1",
            source="wikisource",
            title="T",
            license="http://creativecommons.org/licenses/by-sa/3.0",
        ).license_id
        == "CC-BY-SA-3.0"
    )
    assert Work(id="1", source="gutenberg", title="T").license_id is None


@pytest.mark.parametrize(
    ("license_id", "expected"),
    [
        ("CC-BY-SA-3.0", "https://creativecommons.org/licenses/by-sa/3.0/"),
        ("CC-BY-NC-ND-4.0", "https://creativecommons.org/licenses/by-nc-nd/4.0/"),
        ("CC0-1.0", "https://creativecommons.org/publicdomain/zero/1.0/"),
        # No version, so no canonical page
        ("CC-BY-NC-SA", None),
        ("not-a-license", None),
    ],
)
def test_license_url(license_id, expected):
    assert license_url(license_id) == expected


@pytest.mark.parametrize(
    ("license_id", "expected"),
    [
        (
            "CC-BY-SA-3.0",
            "Creative Commons Attribution-ShareAlike 3.0 (CC BY-SA 3.0)",
        ),
        (
            "CC-BY-NC-ND-4.0",
            (
                "Creative Commons Attribution-NonCommercial-NoDerivatives 4.0"
                " (CC BY-NC-ND 4.0)"
            ),
        ),
        ("CC-BY", "Creative Commons Attribution (CC BY)"),
        ("CC0-1.0", "CC0 1.0 Universal"),
        ("not-a-license", None),
    ],
)
def test_license_label(license_id, expected):
    assert license_label(license_id) == expected
