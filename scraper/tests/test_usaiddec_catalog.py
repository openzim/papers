"""Tests for USAID DEC Archive catalog discovery."""

import csv
import io
import zipfile

import pytest

from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.ports import CatalogFilters
from papers2zim.core.utils import CriticalError
from papers2zim.sources.usaiddec.catalog import (
    CATALOG_FILENAME,
    DEFAULT_CATALOG_URL,
    USAIDDEC_SOURCE,
    UsaidDecCatalog,
    _extract_csv_from_zip,
    _parse_catalog,
    _split_pipe,
    normalize_language,
)

CSV_HEADER = [
    "row_id",
    "Abstract",
    "Ancilary Data",
    "Personal Author",
    "Bibliographic Type Code",
    "Bibtype Name",
    "Contract_Grant_Number",
    "Date of Publication Freeforrm",
    "Date of Publication Fixed",
    "Descriptions from Thesaurus",
    "Secondary Descriptors",
    "Descriptors Geographic",
    "Document ID",
    "Edition",
    "AID Contact Number Evaluated",
    "File Size",
    "USAID Geography Code",
    "USAID Geography Name",
    "New Thesaurus Terms",
    "Institution Authority Code",
    "Institution Name",
    "Institution Role",
    "Language of Text",
    "Primary Subject",
    "Document Title",
    "Series Title",
    "Document Title Translated",
    "Title Word Alternate Spelling",
    "USAID Project Number",
    "Institution or USAID Bureau Author",
    "Institution or USAID Sponsor",
    "Institution or USAID Publisher",
    "Class",
    "DateCreated",
    "inmCreatedBy",
    "Descriptors_Geographic_t",
    "Contract_Number_t",
    "Primary_Subject_t",
    "RegionsAndCities",
    "RegionsAndCities_t",
    "DOI",
    "DigitalObjectIdentifier",
    "[DetailLink]",
    "Formatted Document ID",
    "AidDataURL__PDF",
    "AidDataURL__TXT",
]


def _row(**overrides: str) -> dict[str, str]:
    row = dict.fromkeys(CSV_HEADER, "")
    row.update(
        {
            "row_id": "1",
            "Personal Author": "Doe, Jane",
            "Bibtype Name": "Final Evaluation Report",
            "Date of Publication Fixed": "2020-01",
            "Descriptions from Thesaurus": "Education|Health",
            "Descriptors Geographic": "Kenya",
            "Language of Text": "English",
            "Document Title": "Example Evaluation",
            "Class": "Education (General)",
            "[DetailLink]": "https://dec.usaid.gov/example",
            "Formatted Document ID": "PA000001",
            "AidDataURL__PDF": "https://docs.aiddata.org/ad4/pdfs/usaid-archive/PA000001.pdf",
        }
    )
    row.update(overrides)
    return row


def _csv_text(*rows: dict[str, str]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_HEADER)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def _zip_bytes(csv_text: str, name: str | None = None) -> bytes:
    name = name or (
        "AidData_2000-2024_Archive_of_USAID_DEC_Evaluation_Reports_Dataset_Version_1_0/"
        "AidData_USAID_DEC_Archive_original_source.csv"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, csv_text)
    return output.getvalue()


class StubEngine(DownloadEngine):
    def __init__(self, payload: bytes):
        self.payload = payload
        self.downloaded: list[str] = []

    def fetch_bytes(self, url, headers=None):
        del headers
        self.downloaded.append(url)
        return self.payload


def test_extract_csv_from_zip_finds_original_source_csv():
    payload = _zip_bytes(_csv_text(_row()))
    text = _extract_csv_from_zip(payload)
    assert "Formatted Document ID" in text
    assert "PA000001" in text


def test_parse_catalog_extracts_report_fields():
    (entry,) = _parse_catalog(_csv_text(_row()))

    assert entry.book_id == "PA000001"
    assert entry.title == "Example Evaluation"
    assert entry.language == "en"
    assert entry.authors == ("Doe, Jane",)
    assert entry.pdf_url is not None
    assert entry.pdf_url.endswith("/PA000001.pdf")
    assert entry.subjects[:2] == ("Education", "Health")
    assert entry.geographies == ("Kenya",)


def test_discover_returns_pdf_reports():
    engine = StubEngine(_zip_bytes(_csv_text(_row())))
    catalog = UsaidDecCatalog(engine)

    refs = list(catalog.discover(CatalogFilters(formats=["pdf"])))

    assert [ref.id for ref in refs] == ["PA000001"]
    assert refs[0].source == USAIDDEC_SOURCE
    assert refs[0].extra["languages"] == ["en"]
    assert engine.downloaded == [DEFAULT_CATALOG_URL]


def test_discover_returns_nothing_when_no_supported_format_requested():
    engine = StubEngine(_zip_bytes(_csv_text(_row())))
    catalog = UsaidDecCatalog(engine)

    assert list(catalog.discover(CatalogFilters(formats=["html"]))) == []
    assert engine.downloaded == []


def test_discover_filters_by_formatted_id_and_position():
    rows = _csv_text(
        {
            **_row(row_id="1"),
            "Formatted Document ID": "PA000001",
            "Document Title": "One",
        },
        {
            **_row(row_id="2"),
            "Formatted Document ID": "PA000002",
            "Document Title": "Two",
            "AidDataURL__PDF": "https://docs.aiddata.org/ad4/pdfs/usaid-archive/PA000002.pdf",
        },
    )
    engine = StubEngine(_zip_bytes(rows))
    catalog = UsaidDecCatalog(engine)

    assert [
        ref.id
        for ref in catalog.discover(CatalogFilters(options={"book_ids": ["pa000002"]}))
    ] == ["PA000002"]
    assert [ref.id for ref in catalog.discover(CatalogFilters(book_ids=["1"]))] == [
        "PA000001"
    ]


def test_discover_uses_cached_csv(tmp_path):
    csv_path = tmp_path / CATALOG_FILENAME
    csv_path.write_text(
        _csv_text(
            _row(**{"Formatted Document ID": "PA009999", "Document Title": "Cached"})
        ),
        encoding="utf-8",
    )
    engine = StubEngine(b"unused")
    catalog = UsaidDecCatalog(engine, cache_dir=tmp_path)

    refs = list(catalog.discover(CatalogFilters()))

    assert [ref.id for ref in refs] == ["PA009999"]
    assert engine.downloaded == []


def test_normalize_language_of_blank_values():
    assert normalize_language(None) is None
    assert normalize_language("   ") is None


def test_normalize_language_of_an_unmapped_name_uses_its_iso_code():
    assert normalize_language("Kinyarwanda") == "kin"


def test_split_pipe_drops_blank_items():
    assert _split_pipe(None) == []
    assert _split_pipe("Education | | Health") == ["Education", "Health"]


def test_extract_csv_from_zip_falls_back_to_the_only_csv():
    text = _extract_csv_from_zip(
        _zip_bytes(_csv_text(_row()), name="package/AidData_reports.csv")
    )

    assert "PA000001" in text


def test_extract_csv_from_zip_without_a_csv_is_fatal():
    with pytest.raises(CriticalError):
        _extract_csv_from_zip(_zip_bytes("no tables here", name="package/README.txt"))


def test_parse_catalog_skips_rows_without_an_id_or_a_title():
    entries = _parse_catalog(
        _csv_text(
            _row(row_id="1", **{"Formatted Document ID": ""}),
            _row(row_id="2", **{"Document Title": ""}),
            _row(row_id="3"),
        )
    )

    assert [entry.book_id for entry in entries] == ["PA000001"]


def test_parse_catalog_falls_back_to_the_institution_author():
    (entry,) = _parse_catalog(
        _csv_text(
            _row(
                **{
                    "Personal Author": "Unknown",
                    "Institution or USAID Bureau Author": "USAID/Kenya",
                }
            )
        )
    )

    assert entry.authors == ("USAID/Kenya",)


def test_parse_catalog_keeps_reports_without_any_author():
    (entry,) = _parse_catalog(
        _csv_text(_row(**{"Personal Author": "", "Abstract": "A summary"}))
    )

    assert entry.authors == ()
    assert entry.description == "A summary"


def test_discover_ignores_language_filters_for_explicit_ids():
    catalog = UsaidDecCatalog(StubEngine(_zip_bytes(_csv_text(_row()))))

    refs = catalog.discover(
        CatalogFilters(languages=["fr"], options={"book_ids": ["PA000001"]})
    )

    assert [ref.id for ref in refs] == ["PA000001"]


def test_discover_ignores_language_filters_for_explicit_positions():
    catalog = UsaidDecCatalog(StubEngine(_zip_bytes(_csv_text(_row()))))

    refs = catalog.discover(CatalogFilters(languages=["fr"], book_ids=["1"]))

    assert [ref.id for ref in refs] == ["PA000001"]


def test_discover_filters_reports_by_language():
    rows = _csv_text(
        _row(
            row_id="1",
            **{"Formatted Document ID": "PA000001", "Language of Text": "English"},
        ),
        _row(
            row_id="2",
            **{"Formatted Document ID": "PA000002", "Language of Text": "French"},
        ),
        _row(
            row_id="3",
            **{"Formatted Document ID": "PA000003", "Language of Text": ""},
        ),
    )
    catalog = UsaidDecCatalog(StubEngine(_zip_bytes(rows)))

    assert [ref.id for ref in catalog.discover(CatalogFilters(languages=["eng"]))] == [
        "PA000001",
        "PA000003",
    ]
    assert [ref.id for ref in catalog.discover(CatalogFilters(languages=["en"]))] == [
        "PA000001",
        "PA000003",
    ]
    assert [ref.id for ref in catalog.discover(CatalogFilters(languages=["fr"]))] == [
        "PA000002",
        "PA000003",
    ]


def test_refresh_downloads_the_dataset_and_caches_its_csv(tmp_path):
    engine = StubEngine(_zip_bytes(_csv_text(_row())))
    catalog = UsaidDecCatalog(engine, cache_dir=tmp_path)

    catalog.refresh()

    assert engine.downloaded == [DEFAULT_CATALOG_URL]
    assert (
        (tmp_path / CATALOG_FILENAME).read_text(encoding="utf-8").startswith("row_id")
    )


def test_refresh_without_a_cache_dir_is_fatal():
    catalog = UsaidDecCatalog(StubEngine(b"unused"))

    with pytest.raises(CriticalError):
        catalog.refresh()


def test_refresh_catalog_flag_replaces_the_cached_csv(tmp_path):
    csv_path = tmp_path / CATALOG_FILENAME
    csv_path.write_text(_csv_text(_row(row_id="0")), encoding="utf-8")
    engine = StubEngine(_zip_bytes(_csv_text(_row(row_id="1"))))
    catalog = UsaidDecCatalog(engine, cache_dir=tmp_path, refresh_catalog=True)

    refs = list(catalog.discover(CatalogFilters()))

    assert [ref.id for ref in refs] == ["PA000001"]
    assert engine.downloaded == [DEFAULT_CATALOG_URL]
    assert csv_path.read_text(encoding="utf-8").startswith("row_id")
