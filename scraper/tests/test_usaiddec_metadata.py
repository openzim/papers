"""Tests for USAID DEC Archive metadata conversion."""

from papers2zim.core.ports import WorkRef
from papers2zim.sources.usaiddec.metadata import UsaidDecMetadata


def test_fetch_builds_work_from_catalog_ref():
    metadata = UsaidDecMetadata()
    ref = WorkRef(
        id="PA00JMRT",
        source="usaiddec",
        extra={
            "title": "Evaluation report",
            "description": "Summary",
            "languages": ["en"],
            "authors": ["Doe, Jane"],
            "date_published": "2020-01",
            "pdf_url": "https://docs.aiddata.org/ad4/pdfs/usaid-archive/PA00JMRT.pdf",
            "source_url": "https://dec.usaid.gov/example",
            "class_name": "Education (General)",
            "subjects": ["Education"],
            "geographies": ["Kenya"],
        },
    )

    (work,) = metadata.fetch([ref])

    assert work.id == "PA00JMRT"
    assert work.source == "usaiddec"
    assert work.title == "Evaluation report"
    assert work.description == "Summary"
    assert work.languages == ["en"]
    assert [creator.display_name for creator in work.creators] == ["Doe, Jane"]
    assert work.creators[0].sort_name == "Doe"
    assert work.creators[0].id == "doe-jane-8fa4c16c"
    assert work.published == "2020-01"
    assert work.formats[0].name == "pdf"
    assert work.formats[0].url is not None
    assert work.formats[0].url.endswith("/PA00JMRT.pdf")
    assert [collection.name for collection in work.collections] == ["Education"]
    assert work.collections[0].id == "education"


def test_fetch_skips_blank_authors_and_uses_one_curated_collection():
    ref = WorkRef(
        id="PA00JMRT",
        source="usaiddec",
        extra={
            "title": "Evaluation report",
            "authors": ["Doe, Jane", "   "],
            "class_name": "Basic education",
            "subjects": ["Education", "education", "Health", "Agriculture"],
            "geographies": ["Kenya", "Uganda"],
        },
    )

    (work,) = UsaidDecMetadata().fetch([ref])

    assert [creator.display_name for creator in work.creators] == ["Doe, Jane"]
    assert [collection.name for collection in work.collections] == ["Education"]


def test_author_ids_and_sort_names_are_deterministic():
    ref = WorkRef(
        id="PA00JMRT",
        source="usaiddec",
        extra={"title": "Evaluation report", "authors": ["USAID", "Doe, Jane"]},
    )

    first = next(UsaidDecMetadata().fetch([ref]))
    second = next(UsaidDecMetadata().fetch([ref]))

    assert [creator.id for creator in first.creators] == [
        creator.id for creator in second.creators
    ]
    assert [creator.id for creator in first.creators] == [
        "usaid-eb1461da",
        "doe-jane-8fa4c16c",
    ]
    assert [creator.sort_name for creator in first.creators] == ["USAID", "Doe"]


def test_fetch_ignores_authors_that_are_not_a_list():
    ref = WorkRef(
        id="PA00JMRT",
        source="usaiddec",
        extra={"title": "Evaluation report", "authors": "Doe, Jane"},
    )

    (work,) = UsaidDecMetadata().fetch([ref])

    assert work.creators == []


def test_fetch_preserves_all_report_languages():
    ref = WorkRef(
        id="PA00JMRT",
        source="usaiddec",
        extra={"title": "Evaluation report", "languages": ["fr", "en"]},
    )

    (work,) = UsaidDecMetadata().fetch([ref])

    assert work.languages == ["fr", "en"]


def test_fetch_without_a_pdf_url_yields_a_work_with_no_formats():
    ref = WorkRef(
        id="PA00JMRT", source="usaiddec", extra={"title": "Evaluation report"}
    )

    (work,) = UsaidDecMetadata().fetch([ref])

    assert work.formats == []
    assert work.title == "Evaluation report"
    assert work.languages == ["en"]
