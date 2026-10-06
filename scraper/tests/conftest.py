import io
import zipfile
from unittest.mock import MagicMock

import pytest
from PIL import Image

from papers2zim.core.models import CollectionRef, Cover, Creator, Work


@pytest.fixture
def make_epub():
    """Build a minimal EPUB carrying a single JPEG cover image.

    Call with declared=False to omit the cover declaration, which is how a
    package ends up with only an undeclared image.
    """

    def _make(*, declared: bool = True, size: tuple = (64, 96)) -> bytes:
        image = io.BytesIO()
        Image.new("RGB", size, "white").save(image, format="JPEG")
        meta = '<meta name="cover" content="cover-img"/>' if declared else ""
        properties = ' properties="cover-image"' if declared else ""
        epub = io.BytesIO()
        with zipfile.ZipFile(epub, "w") as archive:
            archive.writestr("mimetype", "application/epub+zip")
            archive.writestr(
                "META-INF/container.xml",
                '<container><rootfiles><rootfile full-path="OPS/package.opf"/>'
                "</rootfiles></container>",
            )
            archive.writestr(
                "OPS/package.opf",
                f"<package><metadata>{meta}</metadata><manifest>"
                f'<item id="cover-img" href="cover.jpg" media-type="image/jpeg"'
                f"{properties}/></manifest></package>",
            )
            archive.writestr("OPS/cover.jpg", image.getvalue())
        return epub.getvalue()

    return _make


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Temporary output folder for ZIMs and downloads"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_creator():
    return Creator(
        id="3485",
        name="James Richardson",
        sort_name="Richardson",
        birth_date=1806,
        death_date=1851,
        extra={
            "first_names": "James",
            "birth_year_raw": "1806",
            "death_year_raw": "1851",
        },
    )


@pytest.fixture
def mock_work(mock_creator):
    return Work(
        id="22094",
        source="gutenberg",
        title="Travels in the Great Desert of Sahara",
        creators=[mock_creator],
        languages=["en"],
        license="Public domain in the USA.",
        cover=Cover(),
        collections=[CollectionRef(id="DT", name="DT", kind="lcc_shelf")],
        popularity=548,
        extra={"has_cover": True},
    )


@pytest.fixture
def mock_zim_creator():
    return MagicMock(name="zim_creator")
