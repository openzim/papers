"""Cover fetching for BNR books."""

from typing import Protocol

from papers2zim.constants import logger
from papers2zim.core.rewriters.image_rewriter import ImageProcessor


class CoverFetchEngine(Protocol):
    """Minimal download interface required to fetch a page cover."""

    def fetch_bytes(self, url: str) -> bytes: ...


def fetch_page_cover(engine: CoverFetchEngine, cover_url: str | None) -> bytes | None:
    """Download and WebP-encode a book page cover."""
    if not cover_url:
        return None
    try:
        return ImageProcessor.optimize_image_content(engine.fetch_bytes(cover_url))
    except Exception as exc:
        logger.debug(
            "Could not fetch Bibliothèque numérique romande page cover %s: %s",
            cover_url,
            exc,
        )
        return None
