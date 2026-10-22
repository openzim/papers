"""One More Library format resolution.

Book pages expose one download link per format, all through a stable
``fid`` query parameter. Metadata keeps the EPUB and PDF links on the work,
so resolution is a lookup instead of a URL construction.
"""

from papers2zim.core.models import Work
from papers2zim.core.ports import DownloadRequest, FormatResolverPort
from papers2zim.sources.onemorelibrary.metadata import FORMAT_MEDIA_TYPES


class OnemorelibraryFormatResolver(FormatResolverPort):
    """Resolve the EPUB or PDF download link of a One More Library book."""

    def resolve(self, work: Work, format_name: str) -> DownloadRequest | None:
        media_type = FORMAT_MEDIA_TYPES.get(format_name)
        if media_type is None:
            return None
        for book_format in work.formats:
            if book_format.name == format_name and book_format.url:
                return DownloadRequest(
                    url=book_format.url,
                    format_name=format_name,
                    extra={"media_type": media_type},
                )
        return None
