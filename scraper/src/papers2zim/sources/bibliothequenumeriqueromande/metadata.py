"""Bibliothèque numérique romande book metadata.

The OPDS entries parsed by `sources.bibliothequenumeriqueromande.catalog` already
carry every field the pipeline needs, so the shared `OpdsMetadata` adapter only
maps a `WorkRef` into a `Work` - there is no per-book fetch.
"""

from papers2zim.core.opds_source import OpdsMetadata
from papers2zim.sources.bibliothequenumeriqueromande.catalog import (
    BNR_LANGUAGE,
    BNR_SOURCE,
)


class BibliothequeNumeriqueRomandeMetadata(OpdsMetadata):
    """Maps discovered BNR `WorkRef`s into `Work`s using the parsed feed data."""

    source = BNR_SOURCE
    default_languages = (BNR_LANGUAGE,)
