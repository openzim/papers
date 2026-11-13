"""Per-work processing for Bibliothèque numérique romande.

Each book is downloaded from its OPDS acquisition links, validated, optimized
and added to the ZIM together with a cover extracted from the book file or,
failing that, the thumbnail advertised in the feed.
"""

from papers2zim.core.opds_source import OpdsPipeline


class BibliothequeNumeriqueRomandePipeline(OpdsPipeline):
    """Download BNR EPUB editions and expose them to the UI readers."""
