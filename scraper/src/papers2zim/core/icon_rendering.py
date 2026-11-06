"""Per-source icon rendering: one SVG in, every raster size a ZIM needs out.

Each source ships a single SVG mark under `core/assets/icons/sources/`. At
export time it is rasterized into every size the ZIM illustration metadata
and the minimal HTML favicon set need, so adding or changing a source's icon
is "drop in one SVG" instead of hand-exporting half a dozen PNGs.
"""

import io
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from PIL import Image
from zimscraperlib.constants import DEFAULT_ZIM_ILLLUSTRATION_SIZE
from zimscraperlib.image.conversion import convert_svg2png
from zimscraperlib.image.illustration import get_zim_illustration

APPLE_TOUCH_ICON_SIZE = 180
MANIFEST_ICON_SIZE_SMALL = 192
MANIFEST_ICON_SIZE_LARGE = 512
FAVICON_ICO_SIZES = (16, 32, 48)


@dataclass(frozen=True, slots=True)
class SourceIconSet:
    """Rasterized icon assets derived from a single source SVG mark."""

    svg_bytes: bytes
    illustration_png: bytes
    favicon_ico: bytes
    apple_touch_icon_png: bytes
    manifest_192_png: bytes
    manifest_512_png: bytes


def resolve_source_icon_svg(filename: str) -> Path:
    """Resolve a source icon filename to its packaged SVG path."""
    resource = (
        resources.files("papers2zim.core") / "assets" / "icons" / "sources" / filename
    )
    if not resource.is_file():
        raise FileNotFoundError(f"Source icon SVG not found: {resource}")
    return Path(str(resource))


def _render_png(svg_fpath: Path, size: int) -> bytes:
    buffer = io.BytesIO()
    convert_svg2png(svg_fpath, buffer, size, size)
    return buffer.getvalue()


def _render_opaque_png(svg_fpath: Path, size: int) -> bytes:
    """Render at `size`, flattened onto a white background (no transparency).

    Apple's Home Screen icon convention expects a fully opaque square since
    iOS applies its own corner rounding and mask.
    """
    with Image.open(io.BytesIO(_render_png(svg_fpath, size))) as source:
        rgba = source.convert("RGBA")
        flattened = Image.new("RGB", rgba.size, (255, 255, 255))
        flattened.paste(rgba, mask=rgba.split()[-1])
        buffer = io.BytesIO()
        flattened.save(buffer, format="PNG")
        return buffer.getvalue()


def _render_favicon_ico(svg_fpath: Path) -> bytes:
    with Image.open(io.BytesIO(_render_png(svg_fpath, max(FAVICON_ICO_SIZES)))) as base:
        buffer = io.BytesIO()
        base.save(
            buffer, format="ICO", sizes=[(size, size) for size in FAVICON_ICO_SIZES]
        )
        return buffer.getvalue()


def build_source_icon_set(svg_fpath: Path) -> SourceIconSet:
    """Rasterize a source's single SVG mark into every icon size a ZIM needs.

    Covers both the 48x48 ZIM illustration metadata and the minimal HTML
    favicon set (favicon.ico, apple-touch-icon.png, web app manifest icons).
    """
    return SourceIconSet(
        svg_bytes=svg_fpath.read_bytes(),
        illustration_png=get_zim_illustration(
            svg_fpath,
            DEFAULT_ZIM_ILLLUSTRATION_SIZE,
            DEFAULT_ZIM_ILLLUSTRATION_SIZE,
        ).getvalue(),
        favicon_ico=_render_favicon_ico(svg_fpath),
        apple_touch_icon_png=_render_opaque_png(svg_fpath, APPLE_TOUCH_ICON_SIZE),
        manifest_192_png=_render_png(svg_fpath, MANIFEST_ICON_SIZE_SMALL),
        manifest_512_png=_render_png(svg_fpath, MANIFEST_ICON_SIZE_LARGE),
    )
