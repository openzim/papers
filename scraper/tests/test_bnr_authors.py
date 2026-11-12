"""Tests for Bibliothèque numérique romande author resolution."""

from unittest.mock import MagicMock

from papers2zim.core.models import Creator
from papers2zim.sources.bibliothequenumeriqueromande.author_enricher import (
    WIKIPEDIA_LANGUAGE,
    BibliothequeNumeriqueRomandeAuthorEnricher,
)


def _creator(name: str) -> Creator:
    return Creator(id="author", display_name=name)


def _enricher(
    engine: MagicMock | None = None,
) -> BibliothequeNumeriqueRomandeAuthorEnricher:
    return BibliothequeNumeriqueRomandeAuthorEnricher(
        engine or MagicMock(name="engine"),
        MagicMock(name="assembler"),
    )


def test_resolve_articles_yields_the_book_author_name():
    engine = MagicMock(name="engine")
    enricher = _enricher(engine)

    articles = list(enricher.resolve_articles(_creator("Charles Perrault")))

    assert articles == [(WIKIPEDIA_LANGUAGE, "Charles Perrault")]
    engine.fetch_bytes.assert_not_called()


def test_resolve_articles_normalizes_the_author_name():
    enricher = _enricher()

    articles = list(enricher.resolve_articles(_creator("  Charles   Perrault ")))

    assert articles == [(WIKIPEDIA_LANGUAGE, "Charles Perrault")]


def test_resolve_articles_returns_nothing_without_a_name():
    engine = MagicMock(name="engine")
    enricher = _enricher(engine)

    assert list(enricher.resolve_articles(_creator("   "))) == []
    engine.fetch_bytes.assert_not_called()


def test_resolve_articles_uses_any_non_empty_name():
    enricher = _enricher()

    assert list(enricher.resolve_articles(_creator("Anonyme"))) == [
        (WIKIPEDIA_LANGUAGE, "Anonyme")
    ]
