"""Wikipedia resolution for Bibliothèque numérique romande authors.

The BNR OPDS feed only carries an author display name: unlike Project
Gutenberg, it provides no curated encyclopedia link to pivot from. Author
details therefore use that book-provided name as-is as the French Wikipedia
article title (BNR only publishes French-language books).
"""

from collections.abc import Iterator

from papers2zim.core.author_enrichment import (
    WikipediaArticle,
    WikipediaAuthorEnricher,
    wikipedia_lang,
)
from papers2zim.core.models import Creator
from papers2zim.sources.bibliothequenumeriqueromande.catalog import BNR_LANGUAGE

WIKIPEDIA_LANGUAGE = wikipedia_lang(BNR_LANGUAGE)


class BibliothequeNumeriqueRomandeAuthorEnricher(WikipediaAuthorEnricher):
    """Wikipedia enricher using the BNR book author name as the article title."""

    def resolve_articles(self, creator: Creator) -> Iterator[WikipediaArticle]:
        """Yield the book-provided author name as the only article candidate."""
        name = " ".join(creator.display_name.split())
        if not name:
            return

        yield (WIKIPEDIA_LANGUAGE, name)
