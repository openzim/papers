"""Bibliothèque numérique romande format resolution.

Every OPDS entry already advertises its EPUB download link, which
`sources.bibliothequenumeriqueromande.metadata` stores on `Work.formats`.
Resolving a format is therefore a lookup on the work, not a URL translation.
"""

from papers2zim.core.models import Work
from papers2zim.core.ports import DownloadRequest, FormatResolverPort


class BibliothequeNumeriqueRomandeFormatResolver(FormatResolverPort):
    """`FormatResolverPort` reading the EPUB link parsed from the feed."""

    def resolve(self, work: Work, format_name: str) -> DownloadRequest | None:
        url = next(
            (fmt.url for fmt in work.formats if fmt.name == format_name and fmt.url),
            None,
        )
        if url is None:
            return None
        return DownloadRequest(url=url, format_name=format_name)
