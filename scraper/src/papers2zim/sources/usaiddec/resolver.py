"""USAID DEC Archive format resolution."""

from papers2zim.core.models import Work
from papers2zim.core.ports import DownloadRequest, FormatResolverPort


class UsaidDecFormatResolver(FormatResolverPort):
    """Resolve the direct PDF download URL of a USAID DEC report."""

    def resolve(self, work: Work, format_name: str) -> DownloadRequest | None:
        if format_name != "pdf":
            return None
        for book_format in work.formats:
            if book_format.name == "pdf" and book_format.url:
                return DownloadRequest(
                    url=book_format.url,
                    format_name="pdf",
                    extra={"media_type": book_format.media_type},
                )
        return None
