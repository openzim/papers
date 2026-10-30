"""Tests for core.exporters.json_exporter with a mocked assembler (no ZIM)."""

import json
import re
from unittest.mock import MagicMock

import pytest

from papers2zim.core.exporters.json_exporter import generate_json_files
from papers2zim.core.index_builder import IndexBuilder
from papers2zim.core.models import CollectionRef, Creator, Work
from papers2zim.core.work_store import WorkStore


def _indexes(store: WorkStore):
    return IndexBuilder(store).build(display_name="Test Source")


def _work(work_id: str, title: str, creator: Creator, shelf: str) -> Work:
    return Work(
        id=work_id,
        source="gutenberg",
        title=title,
        creators=[creator],
        languages=["en"],
        collections=[CollectionRef(id=shelf, name=shelf, kind="lcc_shelf")],
        popularity=100,
        flames=1,
        extra={"has_cover": False},
    )


def _store() -> WorkStore:
    dickens = Creator(id="37", display_name="Charles Dickens")
    austen = Creator(id="68", display_name="Jane Austen")
    store = WorkStore()
    store.add(_work("1", "Bleak House", dickens, "PR"))
    store.add(_work("2", "Emma", austen, "PR"))
    store.add(_work("3", "Oliver Twist", dickens, "PR"))
    return store


def _added_paths(assembler: MagicMock) -> set[str]:
    return {call.kwargs["path"] for call in assembler.add_item_for.call_args_list}


def _config_content(assembler: MagicMock) -> dict:
    call = next(
        call
        for call in assembler.add_item_for.call_args_list
        if call.kwargs["path"] == "config.json"
    )
    return json.loads(call.kwargs["content"])


def _books_content(assembler: MagicMock) -> dict:
    call = next(
        call
        for call in assembler.add_item_for.call_args_list
        if call.kwargs["path"] == "books.json"
    )
    return json.loads(call.kwargs["content"])


def test_generate_json_files_emits_collections():
    assembler = MagicMock(name="assembler")

    store = _store()
    generate_json_files(
        zim_name="test",
        formats=["epub", "html"],
        work_store=store,
        assembler=assembler,
        display_name="Test Source",
        indexes=_indexes(store),
    )

    paths = _added_paths(assembler)
    assert "books.json" in paths
    assert "authors.json" in paths
    assert "collections.json" in paths
    assert "collections/PR.json" in paths
    # per-book and per-author detail files
    assert "books/1.json" in paths
    assert "authors/37.json" in paths


def test_book_previews_export_raw_popularity_and_flames():
    assembler = MagicMock(name="assembler")

    store = _store()
    generate_json_files(
        zim_name="test",
        formats=["html"],
        work_store=store,
        assembler=assembler,
        display_name="Test Source",
        indexes=_indexes(store),
    )

    preview = _books_content(assembler)["books"][0]
    assert preview["popularity"] == 100
    assert preview["flames"] == 1


def test_generate_json_files_does_not_emit_legacy_shelf_files():
    assembler = MagicMock(name="assembler")

    store = _store()
    generate_json_files(
        zim_name="test",
        formats=["html"],
        work_store=store,
        assembler=assembler,
        display_name="Test Source",
        indexes=_indexes(store),
    )

    paths = _added_paths(assembler)
    assert "books.json" in paths
    assert "lcc_shelves.json" not in paths
    assert not any(path.startswith("lcc_shelves/") for path in paths)


def test_collection_detail_path_encodes_unsafe_collection_id():
    assembler = MagicMock(name="assembler")
    creator = Creator(id="1", display_name="Author")
    store = WorkStore()
    store.add(_work("1", "Book", creator, "A/B & C"))

    generate_json_files(
        zim_name="test",
        formats=["html"],
        work_store=store,
        assembler=assembler,
        display_name="Test Source",
        indexes=_indexes(store),
    )

    assert "collections/A%2FB%20%26%20C.json" in _added_paths(assembler)


def test_config_includes_source_theme_and_features():
    assembler = MagicMock(name="assembler")
    store = _store()

    generate_json_files(
        zim_name="test",
        formats=["epub", "pdf"],
        work_store=store,
        assembler=assembler,
        display_name="Open Textbook Library",
        source_slug="opentextbooks",
        source_description="Free textbooks.",
        collection_label="Subjects",
        collection_icon_style="subject",
        indexes=_indexes(store),
    )

    config = _config_content(assembler)
    assert config["source"] == {
        "slug": "opentextbooks",
        "name": "Open Textbook Library",
        "description": "Free textbooks.",
    }
    assert config["theme"]["formatIcons"] == {"epub": "epub", "pdf": "pdf"}
    assert config["theme"]["routeLabels"]["collections"] == "Subjects"
    assert config["theme"]["collectionIconStyle"] == "subject"
    assert config["features"] == {
        "epubReader": True,
        "pdfReader": True,
        "noscriptFallback": True,
        "hasPopularity": True,
        "hasMultipleCollections": False,
    }


def test_config_only_advertises_enabled_readers():
    assembler = MagicMock(name="assembler")
    store = _store()

    generate_json_files(
        zim_name="test",
        formats=["html"],
        work_store=store,
        assembler=assembler,
        display_name="Test Source",
        indexes=_indexes(store),
    )

    assert _config_content(assembler)["features"] == {
        "epubReader": False,
        "pdfReader": False,
        "noscriptFallback": True,
        "hasPopularity": True,
        "hasMultipleCollections": False,
    }


def test_config_reports_a_source_without_popularity():
    assembler = MagicMock(name="assembler")
    store = _store()

    generate_json_files(
        zim_name="test",
        formats=["epub"],
        work_store=store,
        assembler=assembler,
        display_name="Wikisource",
        source_slug="wikisource",
        has_popularity=False,
        indexes=_indexes(store),
    )

    assert _config_content(assembler)["features"]["hasPopularity"] is False


def test_content_info_reports_all_when_nothing_was_filtered():
    assembler = MagicMock(name="assembler")
    store = _store()

    generate_json_files(
        zim_name="test",
        formats=["epub", "pdf", "html"],
        work_store=store,
        assembler=assembler,
        display_name="Test Source",
        indexes=_indexes(store),
    )

    content_info = _config_content(assembler)["contentInfo"]
    assert content_info["source"] == "Test Source"
    assert content_info["collections"] is None
    assert content_info["books"] is None
    assert content_info["languages"] is None
    assert content_info["formats"] is None
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", content_info["dateScraped"])


def test_content_info_reports_explicit_filters():
    assembler = MagicMock(name="assembler")
    store = _store()

    generate_json_files(
        zim_name="test",
        formats=["epub", "pdf"],
        work_store=store,
        assembler=assembler,
        display_name="Test Source",
        indexes=_indexes(store),
        requested_languages=["en"],
        requested_collections=["PR"],
        books=["1", "3"],
    )

    content_info = _config_content(assembler)["contentInfo"]
    assert content_info["collections"] == ["PR"]
    assert sorted(content_info["books"]) == ["Bleak House", "Oliver Twist"]
    assert content_info["languages"] == ["en"]
    assert content_info["formats"] == ["epub", "pdf"]


def test_config_reports_a_single_collection_source():
    assembler = MagicMock(name="assembler")
    store = _store()  # all works share the single "PR" collection

    generate_json_files(
        zim_name="test",
        formats=["html"],
        work_store=store,
        assembler=assembler,
        display_name="Test Source",
        indexes=_indexes(store),
    )

    assert _config_content(assembler)["features"]["hasMultipleCollections"] is False


def test_config_reports_a_source_with_multiple_collections():
    assembler = MagicMock(name="assembler")
    dickens = Creator(id="37", display_name="Charles Dickens")
    austen = Creator(id="68", display_name="Jane Austen")
    store = WorkStore()
    store.add(_work("1", "Bleak House", dickens, "PR"))
    store.add(_work("2", "Emma", austen, "PZ"))

    generate_json_files(
        zim_name="test",
        formats=["html"],
        work_store=store,
        assembler=assembler,
        display_name="Test Source",
        indexes=_indexes(store),
    )

    assert _config_content(assembler)["features"]["hasMultipleCollections"] is True


def test_book_detail_exports_popularity_and_flames():
    assembler = MagicMock(name="assembler")
    creator = Creator(id="1", display_name="Reviewer")
    store = WorkStore()
    store.add(
        Work(
            id="10",
            source="opentextbooks",
            title="Reviewed Textbook",
            creators=[creator],
            popularity=4.07,
            flames=3,
        )
    )

    generate_json_files(
        zim_name="test",
        formats=["pdf"],
        work_store=store,
        assembler=assembler,
        display_name="Open Textbook Library",
        source_slug="opentextbooks",
        indexes=_indexes(store),
    )

    detail_call = next(
        call
        for call in assembler.add_item_for.call_args_list
        if call.kwargs["path"] == "books/10.json"
    )

    detail = json.loads(detail_call.kwargs["content"])
    assert detail["popularity"] == 4.07
    assert detail["flames"] == 3
    assert "primaryMetric" not in detail


def test_author_details_include_wikipedia_enrichment_fields():
    assembler = MagicMock(name="assembler")
    creator = Creator(
        id="68",
        display_name="Jane Austen",
        extra={
            "webpage_resource": "https://en.wikipedia.org/wiki/Jane_Austen",
            "bio": "An English novelist.",
            "portrait_path": "authors/68.webp",
        },
    )
    store = WorkStore()
    store.add(_work("1", "Emma", creator, "PR"))

    generate_json_files(
        zim_name="test",
        formats=["html"],
        work_store=store,
        assembler=assembler,
        display_name="Test Source",
        indexes=_indexes(store),
    )

    detail_call = next(
        call
        for call in assembler.add_item_for.call_args_list
        if call.kwargs["path"] == "authors/68.json"
    )
    detail = json.loads(detail_call.kwargs["content"])
    assert detail["bio"] == "An English novelist."
    assert detail["portraitPath"] == "authors/68.webp"
    assert detail["webpageResource"] == "https://en.wikipedia.org/wiki/Jane_Austen"

    listing_call = next(
        call
        for call in assembler.add_item_for.call_args_list
        if call.kwargs["path"] == "authors.json"
    )
    authors = json.loads(listing_call.kwargs["content"])["authors"]
    assert authors[0]["portraitPath"] == "authors/68.webp"


def test_book_detail_exports_published():
    assembler = MagicMock(name="assembler")
    creator = Creator(id="1", display_name="Reviewer")
    store = WorkStore()
    store.add(
        Work(
            id="10",
            source="wikisource",
            title="Old Book",
            creators=[creator],
            published="c. 1813-1820",
        )
    )

    generate_json_files(
        zim_name="test",
        formats=["pdf"],
        work_store=store,
        assembler=assembler,
        display_name="Wikisource",
        source_slug="wikisource",
        indexes=_indexes(store),
    )

    detail_call = next(
        call
        for call in assembler.add_item_for.call_args_list
        if call.kwargs["path"] == "books/10.json"
    )
    detail = json.loads(detail_call.kwargs["content"])
    assert detail["published"] == "c. 1813-1820"


@pytest.mark.parametrize(
    ("source_license", "expected_id"),
    [
        ("http://creativecommons.org/licenses/by-sa/3.0", "CC-BY-SA-3.0"),
        ("Attribution-NonCommercial", "CC-BY-NC"),
        ("Public domain in the USA.", None),
        (None, None),
    ],
)
def test_book_detail_exports_license_id(source_license, expected_id):
    assembler = MagicMock(name="assembler")
    store = WorkStore()
    store.add(
        Work(
            id="10",
            source="wikisource",
            title="Old Book",
            creators=[Creator(id="1", display_name="Author")],
            license=source_license,
        )
    )

    generate_json_files(
        zim_name="test",
        formats=["pdf"],
        work_store=store,
        assembler=assembler,
        display_name="Wikisource",
        source_slug="wikisource",
        indexes=_indexes(store),
    )

    detail_call = next(
        call
        for call in assembler.add_item_for.call_args_list
        if call.kwargs["path"] == "books/10.json"
    )
    detail = json.loads(detail_call.kwargs["content"])
    assert detail["licenseId"] == expected_id
    # the source's own text stays available as the fallback
    assert detail["license"] == (source_license or "Public domain in the USA.")
