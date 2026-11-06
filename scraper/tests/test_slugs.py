"""Tests for the export-time slug registry."""

from papers2zim.core.models import Creator, Work
from papers2zim.core.slugs import build_slugs


def _work(work_id: str, title: str, creators: list[Creator] | None = None) -> Work:
    return Work(id=work_id, source="test", title=title, creators=creators or [])


def test_build_slugs_uses_readable_title_slugs():
    slugs = build_slugs([_work("1", "Bleak House"), _work("2", "Les Misérables")])

    assert slugs.works == {"1": "bleak-house", "2": "les-misérables"}


def test_build_slugs_suffixes_later_holders_of_a_taken_slug():
    slugs = build_slugs([_work("1", "Bleak House"), _work("2", "Bleak House")])

    assert slugs.works == {"1": "bleak-house", "2": "bleak-house-1"}


def test_build_slugs_reserves_natural_suffixes():
    slugs = build_slugs(
        [
            _work("1", "Bleak House"),
            _work("2", "Bleak House"),
            _work("3", "Bleak House 1"),
        ]
    )

    assert slugs.works["3"] == "bleak-house-1"
    assert slugs.works["2"] == "bleak-house-2"


def test_build_slugs_keeps_work_slugs_clear_of_other_works_source_ids():
    slugs = build_slugs([_work("bleak-house", "Hard Times"), _work("2", "Bleak House")])

    assert slugs.works == {"2": "bleak-house-1", "bleak-house": "hard-times"}


def test_build_slugs_lets_a_work_keep_its_own_source_id_as_slug():
    slugs = build_slugs([_work("bleak-house", "Bleak House")])

    assert slugs.works == {"bleak-house": "bleak-house"}


def test_build_slugs_falls_back_to_the_type_name_when_a_title_slugifies_to_nothing():
    slugs = build_slugs([_work("1", "🎉"), _work("2", "🎉")])

    assert slugs.works == {"1": "book", "2": "book-1"}


def test_build_slugs_assigns_authors_once_per_creator():
    dickens = Creator(id="37", display_name="Charles Dickens")
    slugs = build_slugs(
        [
            _work("1", "Bleak House", [dickens]),
            _work("2", "Oliver Twist", [dickens]),
            _work("3", "Emma", [Creator(id="68", display_name="Jane Austen")]),
        ]
    )

    assert slugs.authors == {"37": "charles-dickens", "68": "jane-austen"}


def test_build_slugs_is_independent_of_catalog_insertion_order():
    works = [_work("1", "Bleak House"), _work("2", "Bleak House")]

    assert build_slugs(works).works == build_slugs(list(reversed(works))).works


def test_build_slugs_covers_works_without_a_creator():
    slugs = build_slugs([_work("1", "Anonymous Work")])

    assert slugs.authors == {"anonymous": "anonymous"}
