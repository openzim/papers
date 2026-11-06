"""Tests for exporting the bundled UI into a ZIM."""

from unittest.mock import MagicMock

from papers2zim.core.exporters.ui_dist_exporter import export_ui_dist


def test_rewrites_the_index_title_and_copies_other_files_as_is(tmp_path):
    (tmp_path / "index.html").write_text(
        "<html><head><title>Library</title></head></html>", encoding="utf-8"
    )
    (tmp_path / "app.js").write_text("console.log('hi')", encoding="utf-8")
    assembler = MagicMock(name="assembler")

    export_ui_dist(tmp_path, "Test Library", assembler)

    calls_by_path = {
        call.kwargs["path"]: call.kwargs
        for call in assembler.add_item_for.call_args_list
    }

    assert calls_by_path["index.html"]["content"] == (
        "<html><head><title>Test Library</title></head></html>"
    )
    assert calls_by_path["index.html"]["mimetype"] == "text/html"
    assert calls_by_path["index.html"]["is_front"] is True

    assert calls_by_path["app.js"]["fpath"] == tmp_path / "app.js"
    assert calls_by_path["app.js"]["is_front"] is False
