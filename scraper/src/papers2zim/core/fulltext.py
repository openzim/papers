"""Full-text indexing of book content.

Each book is indexed once, from the first format by preference among the ones
actually downloaded that yields any text, and its text goes into the book's
search entry (see `core.exporters.search_items_exporter`) so a search hit lands
on the book page, where the user picks the format to read.
"""

from collections.abc import Collection, Sequence

from bs4 import BeautifulSoup
from zimscraperlib.zim.indexing import get_epub_index_data, get_pdf_index_data

from papers2zim.constants import logger

INDEX_FORMAT_PREFERENCE = ("html", "epub", "pdf")

# a line break after these keeps words of adjacent blocks apart, while inline
# markup (e.g. drop caps) does not split words
_BLOCK_TAGS = [
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt",
    "figcaption", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr",
    "li", "main", "nav", "ol", "p", "pre", "section", "table", "td", "th", "tr",
    "ul",
]  # fmt: skip


def index_format_candidates(
    available: Collection[str], forced: str | None = None
) -> list[str]:
    """Formats to try indexing, in order: `forced` first, then by preference"""
    order = [fmt for fmt in INDEX_FORMAT_PREFERENCE if fmt in available]
    if forced in order:
        order.remove(forced)
        order.insert(0, forced)
    return order


def _html_text(html: str | bytes) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "template", "head"]):
        tag.decompose()
    if controls := soup.find(id="html-reader-controls"):
        controls.decompose()
    for tag in soup(_BLOCK_TAGS):
        tag.insert_after("\n")
    return " ".join(soup.get_text().split())


def extract_index_text(
    format_name: str,
    content: str | bytes | Sequence[str | bytes],
    context: str = "",
) -> str:
    """Plain text of a book file (or of all pages of an HTML book), "" on failure"""
    try:
        if format_name == "html":
            pages = [content] if isinstance(content, str | bytes) else content
            return "\n".join(_html_text(page) for page in pages)
        if not isinstance(content, bytes):
            raise TypeError(f"{format_name} content must be bytes")
        if format_name == "epub":
            return get_epub_index_data(content=content).get_content()
        return get_pdf_index_data(content=content).get_content()
    except Exception as exc:
        logger.warning(
            "Could not extract %s text for %s: %s", format_name, context, exc
        )
        return ""
