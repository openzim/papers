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
    assert work.published == "2020-01"
    assert work.formats[0].name == "pdf"
    assert work.formats[0].url is not None
    assert work.formats[0].url.endswith("/PA00JMRT.pdf")
    assert [collection.name for collection in work.collections] == [
        "Education",
        "Kenya",
    ]


def test_fetch_skips_blank_authors_and_repeated_collections():
    ref = WorkRef(
        id="PA00JMRT",
        source="usaiddec",
        extra={
            "title": "Evaluation report",
            "authors": ["Doe, Jane", "   "],
            "subjects": ["Education", "education", "Health", "Agriculture"],
            "geographies": ["Kenya", "Uganda"],
        },
    )

    (work,) = UsaidDecMetadata().fetch([ref])

    assert [creator.display_name for creator in work.creators] == ["Doe, Jane"]
    assert [collection.name for collection in work.collections] == [
        "Education",
        "Health",
        "Kenya",
    ]


def test_fetch_ignores_authors_that_are_not_a_list():
    ref = WorkRef(
        id="PA00JMRT",
        source="usaiddec",
        extra={"title": "Evaluation report", "authors": "Doe, Jane"},
    )

    (work,) = UsaidDecMetadata().fetch([ref])

    assert work.creators == []


def test_fetch_without_a_pdf_url_yields_a_work_with_no_formats():
    ref = WorkRef(
        id="PA00JMRT", source="usaiddec", extra={"title": "Evaluation report"}
    )

    (work,) = UsaidDecMetadata().fetch([ref])

    assert work.formats == []
    assert work.title == "Evaluation report"
    assert work.languages == ["en"]
