"""Tests for ImageProcessor.get_output_filename and WebP conversion decisions."""

import pytest

from papers2zim.core.rewriters.image_rewriter import ImageProcessor


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("001.jpg", "001.jpg.webp"),
        ("001.jpeg", "001.jpeg.webp"),
        ("001.png", "001.png.webp"),
        ("images/001.png", "images/001.png.webp"),
        ("001.webp", "001.webp"),
        ("001.gif", "001.gif"),
        ("notes.txt", "notes.txt"),
    ],
)
def test_get_output_filename(filename: str, expected: str):
    assert ImageProcessor.get_output_filename(filename) == expected


def test_get_output_filename_disambiguates_same_basename_different_extensions():
    """Regression test for #133: images/001.jpg and images/001.png both
    extracted under the same basename must not collapse onto the same
    WebP output path."""
    jpg_output = ImageProcessor.get_output_filename("images/001.jpg")
    png_output = ImageProcessor.get_output_filename("images/001.png")
    assert jpg_output != png_output
