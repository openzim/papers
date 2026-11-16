"""Littérature jeunesse libre book metadata.

The OPDS entries parsed by `sources.litteraturejeunesselibre.catalog` already
carry every field the pipeline needs, so the shared `OpdsMetadata` adapter only
maps a `WorkRef` into a `Work` - there is no per-book fetch.
"""

from papers2zim.core.opds_source import OpdsMetadata
from papers2zim.sources.litteraturejeunesselibre.catalog import LJL_SOURCE

# LJL publishes French-language children's books; fall back to French when an
# entry does not advertise a language.
DEFAULT_LANGUAGE = "fr"


class LitteratureJeunesseLibreMetadata(OpdsMetadata):
    """Maps discovered LJL `WorkRef`s into `Work`s using the parsed feed data."""

    source = LJL_SOURCE
    default_languages = (DEFAULT_LANGUAGE,)
