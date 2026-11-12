"""Gutenberg author enrichment adapter (bio + portrait from Wikipedia).

When `--with-author-bio` and/or `--with-author-portrait` is enabled, the
Gutenberg pipeline enriches every author with a short biography and/or a
portrait sourced from Wikipedia.

The pivot from a Gutenberg author id to its Wikipedia article is the
`pgterms:webpage` link that Project Gutenberg curates inside the author
`pgterms:agent` block of the per-book RDF (see `sources.gutenberg.metadata`).
Unlike sources that only carry an author name, no name matching is needed: the
curated link is authoritative.
"""

from collections.abc import Iterable

from papers2zim.core.author_enrichment import (
    WikipediaArticle,
    WikipediaAuthorEnricher,
    article_from_url,
)
from papers2zim.core.models import Creator


def wikipedia_article(creator: Creator) -> WikipediaArticle | None:
    """Return the (language, title) of the Wikipedia article PG curated."""
    return article_from_url(creator.extra.get("webpage_resource"))


class GutenbergAuthorEnricher(WikipediaAuthorEnricher):
    """Wikipedia enricher pivoting on Project Gutenberg's curated link."""

    def resolve_articles(self, creator: Creator) -> Iterable[WikipediaArticle]:
        """Return the article Project Gutenberg curated for `creator`, if any."""
        article = wikipedia_article(creator)
        return [article] if article else []
