"""Tests for Wikidata-backed Wikisource book descriptions."""

import json
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.models import Work
from papers2zim.core.work_store import WorkStore
from papers2zim.sources.wikisource import description as description_module
from papers2zim.sources.wikisource.description import (
    enrich_work_descriptions,
    fetch_descriptions,
    normalized,
    page_name,
    parse_descriptions,
    sitelink_site,
    work_language,
)


class StubEngine(DownloadEngine):
    def __init__(self, body: bytes):
        self._body = body
        self.fetched: list[str] = []

    def fetch_bytes(self, url: str) -> bytes:
        self.fetched.append(url)
        return self._body


class FailingEngine(DownloadEngine):
    def fetch_bytes(self, _url: str) -> bytes:
        raise requests.RequestException("boom")


def _work(
    work_id: str = "en_w",
    page: str | None = "First_Book",
    lang: str | None = "en",
    description: str | None = None,
) -> Work:
    extra = {"wikisource_page": page} if page is not None else {}
    return Work(
        id=work_id,
        source="wikisource",
        title="A Work",
        languages=[lang] if lang else [],
        description=description,
        extra=extra,
    )


def _entity(title, value, *, lang="en", site=None):
    entity: dict = {"sitelinks": {(site or f"{lang}wikisource"): {"title": title}}}
    if value is not None:
        entity["descriptions"] = {lang: {"value": value}}
    return entity


def _response(entities) -> bytes:
    return json.dumps({"entities": entities, "success": 1}).encode()


def _titles(url: str) -> list[str]:
    return parse_qs(urlparse(url).query)["titles"][0].split("|")


def test_sitelink_site_builds_the_wikisource_site_id():
    assert sitelink_site("fr") == "frwikisource"


def test_page_name_decodes_the_ws_export_page_name():
    work = _work(page="Frankenstein%2C_or_the_Modern_Prometheus")

    assert page_name(work) == "Frankenstein, or the Modern Prometheus"


def test_page_name_is_none_without_a_page():
    assert page_name(_work(page=None)) is None


def test_work_language_is_the_first_language():
    assert work_language(_work(lang="de")) == "de"
    assert work_language(_work(lang=None)) is None


def test_normalized_ignores_case_underscores_and_whitespace():
    assert normalized("  First   Book ") == normalized("first book")


def test_enrich_work_descriptions_sets_descriptions_from_wikidata():
    first = _work("en_a", "1914_and_other_poems")
    second = _work("en_b", "35_Sonnets")
    store = WorkStore()
    store.add(first)
    store.add(second)
    engine = StubEngine(
        _response(
            {
                "Q1": _entity(
                    "1914 and other poems",
                    "debut poetry collection (1915) by Rupert Brooke",
                ),
                "Q2": _entity("35 Sonnets", None),
                "-1": {"sitelinks": {}, "descriptions": {}},
            }
        )
    )

    enrich_work_descriptions(store, engine)

    assert first.description == "debut poetry collection (1915) by Rupert Brooke"
    assert second.description is None


def test_enrich_work_descriptions_declares_the_work_language():
    work = _work("fr_w", "Les_Mis%C3%A9rables", lang="fr")
    store = WorkStore()
    store.add(work)
    engine = StubEngine(
        _response({"Q1": _entity("Les Misérables", "roman", lang="fr")})
    )

    enrich_work_descriptions(store, engine)

    query = parse_qs(urlparse(engine.fetched[0]).query)
    assert query["sites"] == ["frwikisource"]
    assert query["sitefilter"] == ["frwikisource"]
    assert query["languages"] == ["fr"]
    assert work.description == "roman"


def test_enrich_work_descriptions_batches_fifty_titles_per_request():
    store = WorkStore()
    for index in range(55):
        store.add(_work(f"en_{index}", f"Page_{index}"))
    engine = StubEngine(_response({}))

    enrich_work_descriptions(store, engine)

    assert len(engine.fetched) == 2
    assert len(_titles(engine.fetched[0])) == 50
    assert len(_titles(engine.fetched[1])) == 5


def test_enrich_work_descriptions_skips_works_without_page_language_or_description():
    store = WorkStore()
    store.add(_work("en_a", page=None))
    store.add(_work("en_b", lang=None))
    store.add(_work("en_c", description="already there"))
    engine = StubEngine(_response({}))

    enrich_work_descriptions(store, engine)

    assert engine.fetched == []


def test_enrich_work_descriptions_tolerates_request_errors():
    work = _work()
    store = WorkStore()
    store.add(work)

    with patch.object(description_module.logger, "warning") as warning:
        enrich_work_descriptions(store, FailingEngine())

    assert work.description is None
    warning.assert_called_once()


def test_enrich_work_descriptions_tolerates_invalid_json():
    work = _work()
    store = WorkStore()
    store.add(work)

    with patch.object(description_module.logger, "warning") as warning:
        enrich_work_descriptions(store, StubEngine(b"not json"))

    assert work.description is None
    warning.assert_called_once()


def test_parse_descriptions_ignores_incomplete_entities():
    payload = json.dumps(
        {
            "entities": {
                "Q1": {"descriptions": {"en": {"value": "no sitelink"}}},
                "Q2": {"sitelinks": {"enwikisource": {"title": "No description"}}},
                "Q3": {
                    "descriptions": {"en": {"value": ""}},
                    "sitelinks": {"enwikisource": {"title": "Empty value"}},
                },
                "Q4": {
                    "descriptions": {"en": {"value": "bad title"}},
                    "sitelinks": {"enwikisource": {"title": 123}},
                },
                "Q5": _entity("Good Title", "kept"),
            }
        }
    ).encode()

    assert parse_descriptions(payload, "enwikisource", "en") == {
        normalized("Good Title"): "kept"
    }


def test_parse_descriptions_rejects_malformed_entities():
    assert parse_descriptions(b'{"entities": []}', "enwikisource", "en") == {}
    assert parse_descriptions(b'{"success": 1}', "enwikisource", "en") == {}


def test_fetch_descriptions_passes_titles_and_language():
    engine = StubEngine(_response({"Q1": _entity("First Book", "desc")}))

    result = fetch_descriptions(engine, "en", ["First Book", "Second Book"])

    query = parse_qs(urlparse(engine.fetched[0]).query)
    assert query["action"] == ["wbgetentities"]
    assert query["titles"] == ["First Book|Second Book"]
    assert result == {normalized("First Book"): "desc"}


@pytest.mark.parametrize("title", ["First_Book", "First Book", "first_book"])
def test_page_name_and_normalized_match_across_forms(title):
    work = _work(page=title)

    assert normalized(page_name(work) or "") == normalized("First Book")
