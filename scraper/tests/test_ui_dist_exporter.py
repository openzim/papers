"""Tests for exporting the bundled UI into a ZIM."""

from unittest.mock import MagicMock

from papers2zim.constants import FAVICON_BYTES
from papers2zim.core.exporters.ui_dist_exporter import export_ui_dist


def test_exports_fallback_favicon_when_the_ui_build_has_none(tmp_path):
    (tmp_path / "index.html").write_text(
        "<html><head><title>Library</title></head></html>", encoding="utf-8"
    )
    assembler = MagicMock(name="assembler")

    export_ui_dist(tmp_path, "Test Library", assembler)

    favicon_call = next(
        call
        for call in assembler.add_item_for.call_args_list
        if call.kwargs["path"] == "favicon.png"
    )
    assert favicon_call.kwargs == {
        "path": "favicon.png",
        "content": FAVICON_BYTES,
        "mimetype": "image/png",
        "is_front": False,
    }
