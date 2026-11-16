"""Per-work processing for Littérature jeunesse libre.

Each book is downloaded from its OPDS acquisition links, validated, optimized
and added to the ZIM together with a cover extracted from the book file or,
failing that, the thumbnail advertised in the feed.
"""

from papers2zim.core.opds_source import OpdsPipeline


class LitteratureJeunesseLibrePipeline(OpdsPipeline):
    """Download LJL EPUB and PDF editions and expose them to the UI readers."""
