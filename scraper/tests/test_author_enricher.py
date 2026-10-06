"""Tests for gutenberg author enrichment (bio + portrait from Wikipedia)."""

import io
from unittest.mock import MagicMock

import requests
from PIL import Image

from papers2zim.core.models import Creator, Work
from papers2zim.core.work_store import WorkStore
from papers2zim.sources.gutenberg.author_enricher import (
    article_candidates,
    enrich_authors,
    enrich_creator,
    fetch_author_summary,
    fetch_langlink_title,
    wikipedia_article,
    wikipedia_lang,
    zim_language,
)

SUMMARY_JSON = b'{"extract": "A short biography.", "thumbnail": {"source": "https://upload.wikimedia.org/thumb.jpg"}}'

ITALIAN_SUMMARY_JSON = (
    b'{"extract": "Uno scrittore italiano.", '
    b'"thumbnail": {"source": "https://upload.wikimedia.org/thumb-it.jpg"}}'
)

BIO_ONLY_JSON = b'{"extract": "Solo una biografia."}'

LANGLINKS_JSON = (
    b'{"query": {"pages": {"1": {"langlinks": [{"lang": "it", '
    b'"title": "Edmondo De Amicis"}]}}}}'
)


def _jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), "red").save(buffer, format="JPEG")
    return buffer.getvalue()


def _arrow_creator() -> Creator:
    return Creator(
        id="68",
        name="Jane Austen",
        extra={
            "first_names": "Jane",
            "webpage_resource": "https://en.wikipedia.org/wiki/Jane_Austen",
        },
    )


def _amicis_creator() -> Creator:
    return Creator(
        id="61885",
        name="De Amicis, Edmondo",
        extra={
            "webpage_resource": "https://en.wikipedia.org/wiki/Edmondo_De_Amicis",
        },
    )


def _store_with_creator(creator: Creator) -> WorkStore:
    store = WorkStore()
    store.add(Work(id="1", source="gutenberg", title="Emma", creators=[creator]))
    return store


def test_wikipedia_article_extracts_language_and_title():
    assert wikipedia_article(_arrow_creator()) == ("en", "Jane_Austen")
    assert wikipedia_article(
        Creator(
            id="1",
            name="Italian",
            extra={"webpage_resource": "https://it.wikipedia.org/wiki/Guido_da_Verona"},
        )
    ) == ("it", "Guido_da_Verona")
    assert wikipedia_article(
        Creator(
            id="2",
            name="Mobile",
            extra={"webpage_resource": "https://en.m.wikipedia.org/wiki/Jane_Austen"},
        )
    ) == ("en", "Jane_Austen")
    assert wikipedia_article(Creator(id="3", name="No Link")) is None
    assert (
        wikipedia_article(
            Creator(
                id="4",
                name="Personal Site",
                extra={"webpage_resource": "https://example.org/about"},
            )
        )
        is None
    )


def test_wikipedia_lang_maps_iso_639_3_to_wikipedia_code():
    assert wikipedia_lang("fra") == "fr"
    assert wikipedia_lang("deu") == "de"
    assert wikipedia_lang("en") == "en"


def test_zim_language_targets_a_single_requested_language():
    assert zim_language(["fr"]) == "fr"
    assert zim_language(["fra"]) == "fr"
    assert zim_language(["en"]) == "en"


def test_zim_language_is_empty_for_multi_language_or_unset_zims():
    assert zim_language(None) is None
    assert zim_language([]) is None
    assert zim_language(["fr", "en"]) is None


def test_fetch_author_summary_returns_json():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.return_value = SUMMARY_JSON

    summary = fetch_author_summary(engine, "en", "Jane_Austen")
    assert summary is not None
    assert summary["extract"] == "A short biography."
    engine.fetch_bytes.assert_called_once_with(
        "https://en.wikipedia.org/api/rest_v1/page/summary/Jane_Austen"
    )


def test_fetch_author_summary_targets_the_requested_language():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.return_value = ITALIAN_SUMMARY_JSON

    fetch_author_summary(engine, "it", "Edmondo De Amicis")

    engine.fetch_bytes.assert_called_once_with(
        "https://it.wikipedia.org/api/rest_v1/page/summary/Edmondo%20De%20Amicis"
    )


def test_fetch_author_summary_handles_missing_page_and_bad_payload():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.return_value = (
        b'{"type": "https://mediawiki.org/wiki/HyperSwitch/errors/not_found"}'
    )
    assert fetch_author_summary(engine, "en", "No_Such_Author") is None

    engine.fetch_bytes.return_value = b"not json"
    assert fetch_author_summary(engine, "en", "Bad") is None

    def raise_connection_error(*_args, **_kwargs):
        raise requests.ConnectionError("offline")

    engine.fetch_bytes.side_effect = raise_connection_error
    assert fetch_author_summary(engine, "en", "Offline") is None


def test_fetch_langlink_title_reads_title_key():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.return_value = LANGLINKS_JSON

    assert (
        fetch_langlink_title(engine, "en", "Edmondo_De_Amicis", "it")
        == "Edmondo De Amicis"
    )
    url = engine.fetch_bytes.call_args.args[0]
    assert "prop=langlinks" in url
    assert "lllang=it" in url
    assert "en.wikipedia.org/w/api.php" in url


def test_fetch_langlink_title_reads_asterisk_key():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.return_value = (
        b'{"query": {"pages": {"1": {"langlinks": [{"lang": "it", '
        b'"*": "Titolo"}]}}}}'
    )

    assert fetch_langlink_title(engine, "en", "X", "it") == "Titolo"


def test_fetch_langlink_title_handles_absent_link_and_errors():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.return_value = b'{"query": {"pages": {"1": {}}}}'
    assert fetch_langlink_title(engine, "en", "X", "it") is None

    engine.fetch_bytes.return_value = b'{"query": {"pages": []}}'
    assert fetch_langlink_title(engine, "en", "X", "it") is None

    engine.fetch_bytes.return_value = b"not json"
    assert fetch_langlink_title(engine, "en", "X", "it") is None

    def raise_connection_error(*_args, **_kwargs):
        raise requests.ConnectionError("offline")

    engine.fetch_bytes.side_effect = raise_connection_error
    assert fetch_langlink_title(engine, "en", "X", "it") is None


def test_article_candidates_prefers_the_localized_article():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.return_value = LANGLINKS_JSON

    candidates = article_candidates(engine, ("en", "Edmondo_De_Amicis"), "it")
    assert candidates == [("it", "Edmondo De Amicis"), ("en", "Edmondo_De_Amicis")]


def test_article_candidates_skip_lookup_when_language_already_matches():
    engine = MagicMock(name="engine")

    candidates = article_candidates(engine, ("en", "Jane_Austen"), "en")

    assert candidates == [("en", "Jane_Austen")]
    engine.fetch_bytes.assert_not_called()


def test_article_candidates_fall_back_when_no_interlanguage_link_exists():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.return_value = b'{"query": {"pages": {"1": {}}}}'

    candidates = article_candidates(engine, ("en", "Obscure"), "it")

    assert candidates == [("en", "Obscure")]


def test_enrich_creator_sets_bio_portrait_and_skips_without_link():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.side_effect = [SUMMARY_JSON, _jpeg_bytes()]
    assembler = MagicMock(name="assembler")

    enriched = enrich_creator(_arrow_creator(), engine, assembler)

    assert enriched.extra["bio"] == "A short biography."
    assert enriched.extra["portrait_path"] == "authors/68.webp"
    assembler.add_item_for.assert_called_once()
    call = assembler.add_item_for.call_args
    assert call.kwargs["path"] == "authors/68.webp"
    assert call.kwargs["mimetype"] == "image/webp"
    assert isinstance(call.kwargs["content"], bytes) and call.kwargs["content"]

    engine.fetch_bytes.reset_mock()
    unchanged = enrich_creator(Creator(id="216", name="Anonymous"), engine, assembler)
    assert unchanged == Creator(id="216", name="Anonymous")
    engine.fetch_bytes.assert_not_called()


def test_enrich_creator_prefers_localized_bio_and_portrait():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.side_effect = [
        LANGLINKS_JSON,
        ITALIAN_SUMMARY_JSON,
        _jpeg_bytes(),
    ]
    assembler = MagicMock(name="assembler")

    enriched = enrich_creator(_amicis_creator(), engine, assembler, language="it")

    assert enriched.extra["bio"] == "Uno scrittore italiano."
    assert enriched.extra["portrait_path"] == "authors/61885.webp"
    assert engine.fetch_bytes.call_count == 3


def test_enrich_creator_honours_bio_and_portrait_flags_when_localized():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.side_effect = [
        LANGLINKS_JSON,
        ITALIAN_SUMMARY_JSON,
        _jpeg_bytes(),
    ]
    assembler = MagicMock(name="assembler")

    bio_only = enrich_creator(
        _amicis_creator(),
        engine,
        assembler,
        with_bio=True,
        with_portrait=False,
        language="it",
    )

    assert bio_only.extra["bio"] == "Uno scrittore italiano."
    assert "portrait_path" not in bio_only.extra
    assembler.add_item_for.assert_not_called()

    engine.fetch_bytes.side_effect = [
        LANGLINKS_JSON,
        ITALIAN_SUMMARY_JSON,
        _jpeg_bytes(),
    ]
    assembler.reset_mock()

    portrait_only = enrich_creator(
        _amicis_creator(),
        engine,
        assembler,
        with_bio=False,
        with_portrait=True,
        language="it",
    )

    assert "bio" not in portrait_only.extra
    assert portrait_only.extra["portrait_path"] == "authors/61885.webp"
    assembler.add_item_for.assert_called_once()


def test_enrich_creator_skips_lookup_when_both_flags_are_off():
    engine = MagicMock(name="engine")
    assembler = MagicMock(name="assembler")

    unchanged = enrich_creator(
        _amicis_creator(),
        engine,
        assembler,
        with_bio=False,
        with_portrait=False,
        language="it",
    )

    assert unchanged == _amicis_creator()
    engine.fetch_bytes.assert_not_called()
    assembler.add_item_for.assert_not_called()


def test_enrich_creator_falls_back_to_english_portrait_when_local_has_none():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.side_effect = [
        LANGLINKS_JSON,
        BIO_ONLY_JSON,
        SUMMARY_JSON,
        _jpeg_bytes(),
    ]
    assembler = MagicMock(name="assembler")

    enriched = enrich_creator(_amicis_creator(), engine, assembler, language="it")

    assert enriched.extra["bio"] == "Solo una biografia."
    assert enriched.extra["portrait_path"] == "authors/61885.webp"
    assert assembler.add_item_for.call_count == 1


def test_enrich_creator_stops_once_localized_article_is_complete():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.side_effect = [
        LANGLINKS_JSON,
        ITALIAN_SUMMARY_JSON,
        _jpeg_bytes(),
    ]
    assembler = MagicMock(name="assembler")

    enrich_creator(_amicis_creator(), engine, assembler, language="it")

    assert not any(
        "en.wikipedia.org/api/rest_v1" in call.args[0]
        for call in engine.fetch_bytes.call_args_list
    )


def test_enrich_creator_keeps_english_bio_when_no_localized_article():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.side_effect = [
        b'{"query": {"pages": {"1": {}}}}',
        SUMMARY_JSON,
        _jpeg_bytes(),
    ]
    assembler = MagicMock(name="assembler")

    enriched = enrich_creator(_amicis_creator(), engine, assembler, language="it")

    assert enriched.extra["bio"] == "A short biography."
    assert enriched.extra["portrait_path"] == "authors/61885.webp"


def test_enrich_creator_tries_next_article_when_portrait_download_fails():
    engine = MagicMock(name="engine")

    def side_effect(url, **_kwargs):
        if url.startswith("https://it.wikipedia.org/api/rest_v1"):
            return ITALIAN_SUMMARY_JSON
        if url == "https://upload.wikimedia.org/thumb-it.jpg":
            raise requests.ConnectionError("image down")
        if url == "https://upload.wikimedia.org/thumb.jpg":
            return _jpeg_bytes()
        return SUMMARY_JSON

    engine.fetch_bytes.side_effect = side_effect
    assembler = MagicMock(name="assembler")

    enriched = enrich_creator(_amicis_creator(), engine, assembler, language="it")

    assert enriched.extra["portrait_path"] == "authors/61885.webp"
    assembler.add_item_for.assert_called_once()


def test_enrich_creator_without_portrait_keeps_bio_only():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.return_value = b'{"extract": "Only a bio here."}'
    assembler = MagicMock(name="assembler")

    enriched = enrich_creator(_arrow_creator(), engine, assembler)

    assert enriched.extra["bio"] == "Only a bio here."
    assert "portrait_path" not in enriched.extra
    assembler.add_item_for.assert_not_called()


def test_enrich_creator_recovers_from_portrait_errors():
    engine = MagicMock(name="engine")

    def side_effect(url, **_kwargs):
        if url.startswith("https://en.wikipedia.org/api/rest_v1"):
            return SUMMARY_JSON
        raise requests.ConnectionError("image down")

    engine.fetch_bytes.side_effect = side_effect
    assembler = MagicMock(name="assembler")

    enriched = enrich_creator(_arrow_creator(), engine, assembler)

    assert enriched.extra["bio"] == "A short biography."
    assert "portrait_path" not in enriched.extra
    assembler.add_item_for.assert_not_called()


def test_enrich_authors_updates_store_and_deduplicates():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.side_effect = [SUMMARY_JSON, _jpeg_bytes()]
    assembler = MagicMock(name="assembler")

    store = _store_with_creator(_arrow_creator())
    store.add(
        Work(
            id="2",
            source="gutenberg",
            title="Pride and Prejudice",
            creators=[_arrow_creator()],
        )
    )

    enrich_authors(store, engine, assembler, concurrency=2)

    creators = {work.creators[0].id: work.creators[0] for work in store.works}
    assert creators["68"].extra["bio"] == "A short biography."
    assert creators["68"].extra["portrait_path"] == "authors/68.webp"
    assert engine.fetch_bytes.call_count == 2


def test_enrich_authors_prefers_the_requested_zim_language():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.side_effect = [
        LANGLINKS_JSON,
        ITALIAN_SUMMARY_JSON,
        _jpeg_bytes(),
    ]
    assembler = MagicMock(name="assembler")

    store = WorkStore()
    store.add(
        Work(
            id="1",
            source="gutenberg",
            title="Cuore",
            creators=[_amicis_creator()],
            languages=["ita"],
        )
    )

    enrich_authors(store, engine, assembler, concurrency=1, language="it")

    assert store.works[0].creators[0].extra["bio"] == "Uno scrittore italiano."


def test_enrich_authors_keeps_curated_link_without_a_requested_language():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.side_effect = [SUMMARY_JSON, _jpeg_bytes()]
    assembler = MagicMock(name="assembler")

    store = WorkStore()
    store.add(
        Work(
            id="1",
            source="gutenberg",
            title="Emma",
            creators=[_arrow_creator()],
            languages=["en", "fr"],
        )
    )

    enrich_authors(store, engine, assembler, concurrency=1, language=None)

    assert store.works[0].creators[0].extra["bio"] == "A short biography."
    assert engine.fetch_bytes.call_count == 2


def test_enrich_authors_ignores_authors_without_wikipedia():
    engine = MagicMock(name="engine")
    assembler = MagicMock(name="assembler")
    store = _store_with_creator(Creator(id="216", name="Anonymous"))

    enrich_authors(store, engine, assembler, concurrency=1)

    assert store.works[0].creators[0].extra == {}
    engine.fetch_bytes.assert_not_called()
    assembler.add_item_for.assert_not_called()


def test_enrich_authors_keeps_running_when_some_authors_fail():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.side_effect = requests.ConnectionError("offline")
    assembler = MagicMock(name="assembler")
    store = _store_with_creator(_arrow_creator())

    enrich_authors(store, engine, assembler, concurrency=1)

    assert store.works[0].creators[0].extra.get("webpage_resource")
    assert "bio" not in store.works[0].creators[0].extra


def test_enrich_authors_handles_empty_store():
    engine = MagicMock(name="engine")
    assembler = MagicMock(name="assembler")

    enrich_authors(WorkStore(), engine, assembler, concurrency=1)

    engine.fetch_bytes.assert_not_called()
    assembler.add_item_for.assert_not_called()


def test_enrich_creator_skips_bio_when_with_bio_is_false():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.side_effect = [SUMMARY_JSON, _jpeg_bytes()]
    assembler = MagicMock(name="assembler")

    enriched = enrich_creator(
        _arrow_creator(), engine, assembler, with_bio=False, with_portrait=True
    )

    assert "bio" not in enriched.extra
    assert enriched.extra["portrait_path"] == "authors/68.webp"
    assembler.add_item_for.assert_called_once()


def test_enrich_creator_skips_portrait_when_with_portrait_is_false():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.return_value = SUMMARY_JSON
    assembler = MagicMock(name="assembler")

    enriched = enrich_creator(
        _arrow_creator(), engine, assembler, with_bio=True, with_portrait=False
    )

    assert enriched.extra["bio"] == "A short biography."
    assert "portrait_path" not in enriched.extra
    assembler.add_item_for.assert_not_called()


def test_enrich_creator_skips_everything_when_both_disabled():
    engine = MagicMock(name="engine")
    assembler = MagicMock(name="assembler")

    enriched = enrich_creator(
        _arrow_creator(), engine, assembler, with_bio=False, with_portrait=False
    )

    assert "bio" not in enriched.extra
    assert "portrait_path" not in enriched.extra
    engine.fetch_bytes.assert_not_called()
    assembler.add_item_for.assert_not_called()


def test_enrich_authors_fetches_portrait_only_when_with_bio_is_false():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.side_effect = [SUMMARY_JSON, _jpeg_bytes()]
    assembler = MagicMock(name="assembler")

    store = _store_with_creator(_arrow_creator())

    enrich_authors(
        store, engine, assembler, with_bio=False, with_portrait=True, concurrency=1
    )

    creator = store.works[0].creators[0]
    assert "bio" not in creator.extra
    assert creator.extra["portrait_path"] == "authors/68.webp"


def test_enrich_authors_fetches_bio_only_when_with_portrait_is_false():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.return_value = SUMMARY_JSON
    assembler = MagicMock(name="assembler")

    store = _store_with_creator(_arrow_creator())

    enrich_authors(
        store, engine, assembler, with_bio=True, with_portrait=False, concurrency=1
    )

    creator = store.works[0].creators[0]
    assert creator.extra["bio"] == "A short biography."
    assert "portrait_path" not in creator.extra
    assembler.add_item_for.assert_not_called()


def test_enrich_authors_fetches_both_when_both_enabled():
    engine = MagicMock(name="engine")
    engine.fetch_bytes.side_effect = [SUMMARY_JSON, _jpeg_bytes()]
    assembler = MagicMock(name="assembler")

    store = _store_with_creator(_arrow_creator())

    enrich_authors(
        store, engine, assembler, with_bio=True, with_portrait=True, concurrency=1
    )

    creator = store.works[0].creators[0]
    assert creator.extra["bio"] == "A short biography."
    assert creator.extra["portrait_path"] == "authors/68.webp"


def test_enrich_authors_skips_all_when_both_disabled():
    engine = MagicMock(name="engine")
    assembler = MagicMock(name="assembler")

    store = _store_with_creator(_arrow_creator())

    enrich_authors(
        store, engine, assembler, with_bio=False, with_portrait=False, concurrency=1
    )

    creator = store.works[0].creators[0]
    assert "bio" not in creator.extra
    assert "portrait_path" not in creator.extra
    engine.fetch_bytes.assert_not_called()
    assembler.add_item_for.assert_not_called()
