"""Generic image rewriting and WebP conversion helpers.

Source-agnostic: this module contains no source-specific behavior.
"""

import io
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from PIL.Image import Resampling
from PIL.Image import open as pilopen
from zimscraperlib.image.optimization import OptimizeWebpOptions

from papers2zim.constants import logger
from papers2zim.core import optimization_cache

default_webp_options = asdict(OptimizeWebpOptions())


def rewrite_html_image_references(soup: BeautifulSoup, label: str) -> None:
    """Rewrite HTML image references to use .webp extension for converted images."""

    def rewrite_reference(element, attr, ref_type):
        """Helper to rewrite a single reference attribute."""
        if attr in element.attrs and isinstance(element[attr], str):
            old_ref = element[attr]
            if old_ref.startswith(("/", "#")) or urlsplit(old_ref).scheme:
                return
            new_ref = ImageProcessor.get_output_filename(old_ref)
            if old_ref != new_ref:
                element[attr] = new_ref
                logger.debug(f"{label}: Rewrote {ref_type} {old_ref} -> {new_ref}")

    # Rewrite <img> tags
    for img in soup.find_all("img"):
        rewrite_reference(img, "src", "image")

    # Rewrite <link rel="icon"> tags (for cover images in HTML head)
    for link in soup.find_all("link", rel="icon"):
        rewrite_reference(link, "href", "icon")


class ImageProcessor:
    """Centralized image processing logic for conversion decisions and operations."""

    @staticmethod
    def get_extension(filename: str) -> str:
        """Extract lowercase file extension without the dot."""
        return Path(filename).suffix[1:].lower()

    @staticmethod
    def should_convert_to_webp(filename: str) -> bool:
        """Check if file should be converted to WebP (JPG, JPEG, PNG only)."""
        return ImageProcessor.get_extension(filename) in ("jpg", "jpeg", "png")

    @staticmethod
    def get_output_filename(filename: str) -> str:
        """Get output filename with .webp appended if file will be converted.

        The original extension is kept rather than replaced so that two
        source files sharing a basename but differing only in extension
        (e.g. ``001.jpg`` and ``001.png``) don't collide on the same output
        path once both are converted to WebP.

        A query string or fragment is not part of the stored path, so it is
        dropped before the extension is inspected; otherwise the ``.webp``
        suffix would land after the query (``cover.jpg?v=2.webp``) instead of
        naming the stored file (``cover.jpg.webp``).
        """
        path = urlsplit(filename).path or filename
        if ImageProcessor.should_convert_to_webp(path):
            return f"{path}.webp"
        return path

    @staticmethod
    def optimize_image_content(
        file_content: bytes, max_width: int | None = None
    ) -> bytes:
        """Convert and optimize image content to WebP format.

        When max_width is set, images wider than that are scaled down
        (never up) before conversion.

        Results are cached by input content when a cache directory is
        configured, so identical artwork is only encoded once per run of the
        scraper against a given cache.
        """

        def _convert() -> bytes:
            dst = io.BytesIO()
            with pilopen(io.BytesIO(file_content)) as image:
                if max_width is not None and image.width > max_width:
                    image.thumbnail((max_width, image.height), Resampling.LANCZOS)
                image.save(dst, format="WEBP", **default_webp_options)
            return dst.getvalue()

        return optimization_cache.get_or_compute(
            file_content,
            {
                "target": "webp",
                "max_width": max_width,
                "options": default_webp_options,
            },
            _convert,
        )
