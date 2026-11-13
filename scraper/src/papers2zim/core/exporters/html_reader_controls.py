"""Export the reader controls shared by HTML-capable sources."""

import posixpath
from importlib import resources
from urllib.parse import quote

from bs4 import BeautifulSoup

from papers2zim.constants import logger
from papers2zim.core.models import Work
from papers2zim.core.utils import archive_name_for
from papers2zim.core.zim_assembler import ZimAssembler

_READER_CONTROL_ASSETS = (
    ("css/html-reader-controls.css", "text/css"),
    ("js/html-reader-controls.js", "text/javascript"),
    ("icons/info.svg", "image/svg+xml"),
    ("icons/epub.svg", "image/svg+xml"),
    ("icons/pdf.svg", "image/svg+xml"),
    ("icons/scroll-up.svg", "image/svg+xml"),
)


def export_html_reader_control_assets(assembler: ZimAssembler) -> None:
    """Export shared HTML reader controls and icons to the ZIM."""
    assets_dir = resources.files("papers2zim.core") / "assets"

    for zim_path, mimetype in _READER_CONTROL_ASSETS:
        resource = assets_dir.joinpath(*zim_path.split("/"))
        if not resource.is_file():
            raise FileNotFoundError(f"HTML reader control asset not found: {resource}")
        logger.debug(f"Adding {zim_path} to ZIM")
        assembler.add_item_for(
            path=zim_path,
            content=resource.read_bytes(),
            mimetype=mimetype,
            is_front=False,
        )


def inject_reader_controls(
    soup: BeautifulSoup, page_path: str, work: Work, formats: list[str]
) -> None:
    """Add shared reader controls and available binary downloads to an HTML page."""
    html = soup.html or soup.new_tag("html")
    if soup.html is None:
        soup.append(html)
    head = soup.head
    if head is None:
        head = soup.new_tag("head")
        html.insert(0, head)
    body = soup.body
    if body is None:
        body = soup.new_tag("body")
        html.append(body)

    assets_base = posixpath.relpath(".", posixpath.dirname(page_path)) or "."
    index_path = posixpath.relpath("index.html", posixpath.dirname(page_path))
    css_path = f"{assets_base}/css/html-reader-controls.css"
    js_path = f"{assets_base}/js/html-reader-controls.js"
    if not head.find("link", href=css_path):
        stylesheet = soup.new_tag("link", rel="stylesheet", href=css_path)
        stylesheet["type"] = "text/css"
        head.append(stylesheet)

    if not body.find(id="html-reader-controls"):
        controls = soup.new_tag("div", id="html-reader-controls")
        info = soup.new_tag(
            "a",
            attrs={
                "href": f"{index_path}#/book/{quote(work.id, safe='')}",
                "class": "html-reader-btn html-reader-btn-info",
                "aria-label": "View book cover and information",
                "title": "View book cover and information",
            },
        )
        info.append(
            soup.new_tag(
                "img",
                src=f"{assets_base}/icons/info.svg",
                alt="Info",
                width="24",
                height="24",
            )
        )
        controls.append(info)
        for format_name in formats:
            if format_name not in {"epub", "pdf"}:
                continue
            archive_path = archive_name_for(work, format_name)
            download = soup.new_tag(
                "a",
                attrs={
                    "href": encode_url_path(
                        posixpath.relpath(archive_path, posixpath.dirname(page_path))
                    ),
                    "class": f"html-reader-btn html-reader-btn-{format_name}",
                    "aria-label": f"Download {format_name.upper()} format",
                    "title": f"Download {format_name.upper()} format",
                },
            )
            download.append(
                soup.new_tag(
                    "img",
                    src=f"{assets_base}/icons/{format_name}.svg",
                    alt=format_name.upper(),
                    width="24",
                    height="24",
                )
            )
            controls.append(download)
        scroll = soup.new_tag(
            "a",
            attrs={
                "href": "#",
                "id": "scroll-to-top",
                "class": "html-reader-btn html-reader-btn-up hidden",
                "aria-label": "Scroll to top",
                "title": "Scroll to top",
            },
        )
        scroll.append(
            soup.new_tag(
                "img",
                src=f"{assets_base}/icons/scroll-up.svg",
                alt="Scroll to top",
                width="24",
                height="24",
            )
        )
        controls.append(scroll)
        body.insert(0, controls)
    if not body.find("script", src=js_path):
        script = soup.new_tag("script", src=js_path)
        script["type"] = "text/javascript"
        body.append(script)


def encode_url_path(path: str) -> str:
    """Percent-encode each segment of a relative URL path."""
    return "/".join(quote(segment, safe="") for segment in path.split("/"))
