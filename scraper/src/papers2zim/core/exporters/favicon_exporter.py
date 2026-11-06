"""Favicon / web-app-manifest icon set exporter.

Adds the minimal 2026-appropriate icon set for HTML pages served from a ZIM:
favicon.svg, favicon.ico (legacy fallback), apple-touch-icon.png and the web
app manifest icons + site.webmanifest. Every reference is relative so it
resolves correctly under kiwix-serve's content namespacing.
"""

import json

from papers2zim.constants import logger
from papers2zim.core.icon_rendering import SourceIconSet
from papers2zim.core.zim_assembler import ZimAssembler

MANIFEST_FILENAME = "site.webmanifest"


def export_favicons(
    icon_set: SourceIconSet, title: str, assembler: ZimAssembler
) -> None:
    """Add the shared favicon/web-app-manifest icon set to the ZIM root."""
    logger.info("Adding favicon and web app manifest icons")

    assembler.add_item_for(
        path="favicon.svg",
        content=icon_set.svg_bytes,
        mimetype="image/svg+xml",
        is_front=False,
    )
    assembler.add_item_for(
        path="favicon.ico",
        content=icon_set.favicon_ico,
        mimetype="image/vnd.microsoft.icon",
        is_front=False,
    )
    assembler.add_item_for(
        path="apple-touch-icon.png",
        content=icon_set.apple_touch_icon_png,
        mimetype="image/png",
        is_front=False,
    )
    assembler.add_item_for(
        path="web-app-manifest-192x192.png",
        content=icon_set.manifest_192_png,
        mimetype="image/png",
        is_front=False,
    )
    assembler.add_item_for(
        path="web-app-manifest-512x512.png",
        content=icon_set.manifest_512_png,
        mimetype="image/png",
        is_front=False,
    )
    manifest = {
        "name": title,
        "short_name": title,
        "icons": [
            {
                "src": "web-app-manifest-192x192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "maskable",
            },
            {
                "src": "web-app-manifest-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
        "theme_color": "#ffffff",
        "background_color": "#ffffff",
        "display": "standalone",
    }
    assembler.add_item_for(
        path=MANIFEST_FILENAME,
        content=json.dumps(manifest),
        mimetype="application/manifest+json",
        is_front=False,
    )
