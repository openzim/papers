"""Tests for exporting the favicon / web-app-manifest icon set to the ZIM."""

import json
from unittest.mock import MagicMock

from papers2zim.core.exporters.favicon_exporter import export_favicons
from papers2zim.core.icon_rendering import SourceIconSet


def _icon_set() -> SourceIconSet:
    return SourceIconSet(
        svg_bytes=b"<svg/>",
        illustration_png=b"illustration",
        favicon_ico=b"ico",
        apple_touch_icon_png=b"apple",
        manifest_192_png=b"192",
        manifest_512_png=b"512",
    )


def test_export_favicons_adds_every_icon_file_at_the_zim_root():
    assembler = MagicMock(name="assembler")

    export_favicons(_icon_set(), "Test Library", assembler)

    calls_by_path = {
        call.kwargs["path"]: call.kwargs
        for call in assembler.add_item_for.call_args_list
    }

    assert calls_by_path["favicon.svg"]["content"] == b"<svg/>"
    assert calls_by_path["favicon.svg"]["mimetype"] == "image/svg+xml"
    assert calls_by_path["favicon.ico"]["content"] == b"ico"
    assert calls_by_path["apple-touch-icon.png"]["content"] == b"apple"
    assert calls_by_path["web-app-manifest-192x192.png"]["content"] == b"192"
    assert calls_by_path["web-app-manifest-512x512.png"]["content"] == b"512"

    manifest = json.loads(calls_by_path["site.webmanifest"]["content"])
    assert manifest["name"] == "Test Library"
    assert manifest["icons"] == [
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
    ]
    assert calls_by_path["site.webmanifest"]["mimetype"] == "application/manifest+json"
