"""Generic cover extraction from downloaded book files.

Format-level helpers shared across sources: covers are derived from the
downloaded source file, either the first PDF page or the EPUB package's
declared cover image. Source-specific page-cover discovery lives with the
source that needs it.
"""

import io
import zipfile
from pathlib import PurePosixPath
from urllib.parse import unquote, urldefrag

import pymupdf
from lxml import etree  # pyright: ignore[reportAttributeAccessIssue]

from papers2zim.constants import logger
from papers2zim.core.rewriters.image_rewriter import ImageProcessor


def extract_cover(
    content: bytes,
    format_name: str,
    *,
    max_width: int | None = None,
    declared_only: bool = False,
) -> bytes | None:
    """Extract and WebP-encode a cover image from a downloaded book file.

    max_width scales the result down (never up) before encoding.
    declared_only restricts EPUB covers to the image the package explicitly
    declares as its cover, instead of falling back to the first image found.
    """
    try:
        if format_name == "pdf":
            image = _pdf_first_page(content)
        elif format_name == "epub":
            image = _epub_cover(content, declared_only=declared_only)
        else:
            return None
        if not image:
            return None
        return ImageProcessor.optimize_image_content(image, max_width=max_width)
    except Exception as exc:
        logger.debug("Could not extract %s cover: %s", format_name, exc)
        return None


def _pdf_first_page(content: bytes) -> bytes | None:
    document = pymupdf.open(stream=content, filetype="pdf")
    try:
        if document.page_count == 0:
            return None
        pixmap = document[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
        return pixmap.tobytes("png")
    finally:
        document.close()


def _epub_cover(content: bytes, *, declared_only: bool = False) -> bytes | None:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        container = etree.fromstring(archive.read("META-INF/container.xml"), parser)
        rootfile = container.find(".//{*}rootfile")
        if rootfile is None or not (opf_path := rootfile.get("full-path")):
            return None

        package = etree.fromstring(archive.read(opf_path), parser)
        manifest = {
            item.get("id"): item
            for item in package.findall(".//{*}manifest/{*}item")
            if item.get("id") and item.get("href")
        }
        cover_id = next(
            (
                meta.get("content")
                for meta in package.findall(".//{*}metadata/{*}meta")
                if meta.get("name") == "cover" and meta.get("content")
            ),
            None,
        )
        cover_item = manifest.get(cover_id) if cover_id else None
        if cover_item is None and not declared_only:
            cover_item = next(
                (
                    item
                    for item in manifest.values()
                    if "cover-image" in item.get("properties", "").split()
                ),
                None,
            )
        if cover_item is None and not declared_only:
            cover_item = next(
                (
                    item
                    for item in manifest.values()
                    if item.get("media-type", "").startswith("image/")
                ),
                None,
            )
        if cover_item is None:
            return None

        href = unquote(urldefrag(cover_item.attrib["href"])[0])
        cover_path = PurePosixPath(opf_path).parent / href
        return archive.read(str(cover_path))
