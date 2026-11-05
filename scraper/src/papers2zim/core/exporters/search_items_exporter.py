"""Search items exporter: writes the ZIM full-text/title index entries.

These are not JSON files but tiny HTML redirect pages (`index/<fname>`)
pointing at Vue.js UI routes, wrapped with `IndexData` so the ZIM search
index picks them up. The entries themselves are derived once by
`core.index_builder.IndexBuilder`; this module only owns the on-ZIM
encoding and writing.
"""

from html import escape

from zimscraperlib.zim.indexing import IndexData

from papers2zim.constants import logger
from papers2zim.core.index_builder import Indexes, book_search_entry
from papers2zim.core.models import Work
from papers2zim.core.zim_assembler import ZimAssembler


def add_search_item(
    title: str,
    content: str,
    fname: str,
    vue_route: str,
    assembler: ZimAssembler,
    index_text: str = "",
) -> None:
    """Add a custom item to the ZIM index with HTML redirect to Vue.js route.

    Args:
        title: Title for the index entry
        content: Content/description for search indexing
        fname: Filename for the index entry (e.g., "book_12345")
        vue_route: Vue.js route path (e.g., "book/12345")
        assembler: The ZIM assembler to add the item to
        index_text: Extra text indexed but not stored (e.g. the book text)
    """
    redirect_url = f"../index.html#/{vue_route}"
    safe_title = escape(title)
    safe_content = escape(content)
    safe_redirect_url = escape(redirect_url, quote=True)
    html_content = (
        f"<html><head><title>{safe_title}</title>"
        f'<meta http-equiv="refresh" content="0;URL=\'{safe_redirect_url}\'" />'
        f"</head><body>{safe_content}</body></html>"
    )

    logger.debug(f"Adding {fname} to ZIM index")
    assembler.add_item_for(
        title=title,
        path=f"index/{fname}",
        content=html_content,
        mimetype="text/html",
        index_data=IndexData(
            title=title, content=f"{content}\n{index_text}" if index_text else content
        ),
    )


def export_book_search_item(
    work: Work, index_text: str, assembler: ZimAssembler
) -> None:
    """Write the search entry of one book, indexing its text too"""
    entry = book_search_entry(work)
    add_search_item(
        title=entry.title,
        content=entry.content,
        fname=entry.fname,
        vue_route=entry.route,
        assembler=assembler,
        index_text=index_text,
    )


def export_search_items(indexes: Indexes, assembler: ZimAssembler) -> None:
    """Write the derived search entries (authors, collections, listings)"""
    logger.debug("Generating ZIM index entries")
    for entry in indexes.search_entries:
        add_search_item(
            title=entry.title,
            content=entry.content,
            fname=entry.fname,
            vue_route=entry.route,
            assembler=assembler,
        )
