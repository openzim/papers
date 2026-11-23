from io import BytesIO
from pathlib import Path

from libzim.reader import Archive
from PIL import Image

from papers2zim.core.zim_assembler import ZimAssembler


def _illustration() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (48, 48), "red").save(buffer, format="PNG")
    return buffer.getvalue()


def _assembler(path: Path) -> ZimAssembler:
    return ZimAssembler(
        filename=path,
        language="eng",
        title="Test ZIM",
        description="Test description",
        name="test-zim",
        publisher="Test publisher",
        source_creator="Test creator",
        tags="test",
        illustration_png=_illustration(),
        with_fulltext_index=False,
    )


def _start(assembler: ZimAssembler) -> None:
    assembler.start()
    assembler.add_item_for(
        path="index.html", content=b"<html>ok</html>", mimetype="text/html"
    )


def test_deduplicates_image_content(tmp_path: Path):
    path = tmp_path / "content.zim"
    assembler = _assembler(path)
    _start(assembler)
    image = b"same-image-content"

    assembler.add_item_for(
        path="html/1/assets/first.webp", content=image, mimetype="image/webp"
    )
    assembler.add_item_for(
        path="html/2/assets/second.webp", content=image, mimetype="image/webp"
    )
    assembler.finish()

    archive = Archive(path)
    assert archive.media_count == 1
    assert (
        bytes(archive.get_entry_by_path("html/1/assets/first.webp").get_item().content)
        == image
    )
    assert (
        bytes(archive.get_entry_by_path("html/2/assets/second.webp").get_item().content)
        == image
    )


def test_deduplicates_image_files(tmp_path: Path):
    path = tmp_path / "files.zim"
    assembler = _assembler(path)
    _start(assembler)
    first = tmp_path / "first.jpg"
    second = tmp_path / "second.jpg"
    first.write_bytes(b"same-image-content")
    second.write_bytes(b"same-image-content")

    assembler.add_item_for(
        path="html/1/assets/first.jpg", fpath=first, mimetype="image/jpeg"
    )
    assembler.add_item_for(
        path="html/2/assets/second.jpg", fpath=second, mimetype="image/jpeg"
    )
    assembler.finish()

    archive = Archive(path)
    assert archive.media_count == 1
    assert archive.has_entry_by_path("html/1/assets/first.jpg")
    assert archive.has_entry_by_path("html/2/assets/second.jpg")


def test_keeps_duplicate_non_image_content(tmp_path: Path):
    path = tmp_path / "non-image.zim"
    assembler = _assembler(path)
    _start(assembler)

    assembler.add_item_for(path="first.txt", content=b"same", mimetype="text/plain")
    assembler.add_item_for(path="second.txt", content=b"same", mimetype="text/plain")
    assembler.finish()

    archive = Archive(path)
    assert archive.media_count == 0
    assert bytes(archive.get_entry_by_path("first.txt").get_item().content) == b"same"
    assert bytes(archive.get_entry_by_path("second.txt").get_item().content) == b"same"
