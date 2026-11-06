"""Tests for rasterizing a source's SVG mark into the ZIM/HTML icon set."""

import io

import pytest
from PIL import Image

from papers2zim.core.icon_rendering import (
    APPLE_TOUCH_ICON_SIZE,
    FAVICON_ICO_SIZES,
    MANIFEST_ICON_SIZE_LARGE,
    MANIFEST_ICON_SIZE_SMALL,
    build_source_icon_set,
    resolve_source_icon_svg,
)

SIMPLE_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    b'<rect width="100" height="100" fill="#ff0000"/></svg>'
)


@pytest.fixture
def svg_fpath(tmp_path):
    fpath = tmp_path / "source.svg"
    fpath.write_bytes(SIMPLE_SVG)
    return fpath


def test_resolve_source_icon_svg_finds_a_registered_source_icon():
    fpath = resolve_source_icon_svg("gutenberg.svg")

    assert fpath.is_file()


def test_resolve_source_icon_svg_rejects_an_unknown_filename():
    with pytest.raises(FileNotFoundError):
        resolve_source_icon_svg("does-not-exist.svg")


def test_build_source_icon_set_renders_every_expected_size(svg_fpath):
    icon_set = build_source_icon_set(svg_fpath)

    assert icon_set.svg_bytes == SIMPLE_SVG
    assert Image.open(io.BytesIO(icon_set.illustration_png)).size == (48, 48)
    assert Image.open(io.BytesIO(icon_set.apple_touch_icon_png)).size == (
        APPLE_TOUCH_ICON_SIZE,
        APPLE_TOUCH_ICON_SIZE,
    )
    assert Image.open(io.BytesIO(icon_set.manifest_192_png)).size == (
        MANIFEST_ICON_SIZE_SMALL,
        MANIFEST_ICON_SIZE_SMALL,
    )
    assert Image.open(io.BytesIO(icon_set.manifest_512_png)).size == (
        MANIFEST_ICON_SIZE_LARGE,
        MANIFEST_ICON_SIZE_LARGE,
    )

    favicon = Image.open(io.BytesIO(icon_set.favicon_ico))
    assert favicon.info["sizes"] == {(size, size) for size in FAVICON_ICO_SIZES}


def test_apple_touch_icon_is_opaque(svg_fpath):
    icon_set = build_source_icon_set(svg_fpath)

    assert Image.open(io.BytesIO(icon_set.apple_touch_icon_png)).mode == "RGB"
