"""USAID DEC Archive catalog access backed by the AidData dataset CSV.

The AidData dataset is distributed as a ZIP file containing a CSV with
metadata and permanent PDF/TXT URLs for each evaluation report. The
catalog downloads and caches that CSV for discovery and filtering.
"""

import csv
import io
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import babel

from papers2zim.constants import logger
from papers2zim.core.download_engine import DownloadEngine
from papers2zim.core.language import ISO_MATRIX, ISO_MATRIX_REV
from papers2zim.core.ports import CatalogFilters, CatalogPort, WorkRef
from papers2zim.core.utils import critical_error

USAIDDEC_SOURCE = "usaiddec"
CATALOG_FILENAME = "usaiddec_catalog.csv"
DEFAULT_CATALOG_URL = (
    "https://docs.aiddata.org/ad4/datasets/"
    "AidData_2000-2024_Archive_of_USAID_DEC_Evaluation_Reports_Dataset_Version_1_0.zip"
)
SUPPORTED_FORMATS = frozenset({"pdf"})


@lru_cache(maxsize=1)
def _language_name_codes() -> dict[str, str]:
    """Map English language names ("French") to ISO 639-1 codes ("fr").

    Babel ships the CLDR names, so this stays in sync with the ISO matrix in
    ``papers2zim.core.language`` instead of duplicating a hand-written map.
    """
    codes: dict[str, str] = {}
    for code in ISO_MATRIX:
        try:
            name = babel.Locale(code).get_language_name("en")
        except (babel.UnknownLocaleError, ValueError) as exc:
            logger.debug("Cannot resolve the name of language %r: %s", code, exc)
            continue
        if name:
            codes.setdefault(name.casefold(), code)
    return codes


def normalize_language(value: str | None) -> str | None:
    """Normalize a dataset language label to a valid ISO 639-1 code.

    Accepts ISO codes (``en``/``eng``) as well as English language names
    (``English``). Unrecognized labels yield ``None`` rather than an invented
    code such as ``ger``/``hai``, which would surface as a raw fragment in the
    UI and silently break ``--languages`` filtering.
    """
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    key = text.casefold()
    if key in ISO_MATRIX:
        return key
    if key in ISO_MATRIX_REV:
        return ISO_MATRIX_REV[key]
    code = _language_name_codes().get(key)
    if code is None:
        logger.warning("Ignoring unrecognized USAID DEC language label %r", text)
    return code


def _split_pipe(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split("|") if item.strip()]


def normalize_languages(value: str | None) -> tuple[str, ...]:
    """Normalize a pipe-separated language field into ISO 639-1 codes.

    Reports are often bilingual ("French|English"), so each label is resolved
    independently and duplicates are dropped while keeping dataset order.
    """
    codes: list[str] = []
    for label in _split_pipe(value):
        code = normalize_language(label)
        if code and code not in codes:
            codes.append(code)
    return tuple(codes)


@dataclass(frozen=True, slots=True)
class UsaidDecEntry:
    book_id: str
    title: str
    description: str | None
    languages: tuple[str, ...]
    authors: tuple[str, ...]
    date_published: str | None
    pdf_url: str | None
    source_url: str | None
    file_size: str | None
    bibtype: str | None
    class_name: str | None
    subjects: tuple[str, ...]
    geographies: tuple[str, ...]


def _extract_csv_from_zip(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        csv_names = [
            name
            for name in archive.namelist()
            if name.endswith(".csv")
            and "original_source" in name.lower()
            and "__MACOSX" not in name
        ]
        if not csv_names:
            csv_names = [
                name
                for name in archive.namelist()
                if name.endswith(".csv") and "__MACOSX" not in name
            ]
        if not csv_names:
            critical_error("USAID DEC dataset ZIP does not contain a CSV file")
        return archive.read(csv_names[0]).decode("utf-8-sig")


def _parse_catalog(csv_text: str) -> list[UsaidDecEntry]:
    reader = csv.DictReader(io.StringIO(csv_text))
    entries: list[UsaidDecEntry] = []
    for row in reader:
        book_id = (row.get("Formatted Document ID") or "").strip()
        if not book_id:
            continue
        title = (row.get("Document Title") or "").strip()
        if not title:
            continue
        abstract = (row.get("Abstract") or "").strip() or None
        ancillary = (row.get("Ancilary Data") or "").strip() or None
        description = abstract or ancillary
        authors = tuple(
            name
            for name in _split_pipe(row.get("Personal Author"))
            if name and name.casefold() != "unknown"
        )
        if not authors:
            inst_author = (row.get("Institution or USAID Bureau Author") or "").strip()
            if inst_author:
                authors = (inst_author,)
        class_value = (row.get("Class") or "").strip()
        subject_values = [
            *_split_pipe(row.get("Descriptions from Thesaurus")),
            *([class_value] if class_value else []),
        ]
        subjects = tuple(dict.fromkeys(s for s in subject_values if s))
        geographies = tuple(
            s for s in _split_pipe(row.get("Descriptors Geographic")) if s
        )
        date_published = (
            (row.get("Date of Publication Fixed") or "").strip()
            or (row.get("Date of Publication Freeforrm") or "").strip()
            or None
        )
        pdf_url = (row.get("AidDataURL__PDF") or "").strip() or None
        entries.append(
            UsaidDecEntry(
                book_id=book_id,
                title=title,
                description=description,
                languages=normalize_languages(row.get("Language of Text")),
                authors=authors,
                date_published=date_published,
                pdf_url=pdf_url,
                source_url=(row.get("[DetailLink]") or "").strip() or None,
                file_size=(row.get("File Size") or "").strip() or None,
                bibtype=(row.get("Bibtype Name") or "").strip() or None,
                class_name=class_value or None,
                subjects=subjects,
                geographies=geographies,
            )
        )
    return entries


class UsaidDecCatalog(CatalogPort):
    """Discover USAID DEC evaluation reports from the AidData dataset CSV."""

    def __init__(
        self,
        engine: DownloadEngine,
        base_url: str = DEFAULT_CATALOG_URL,
        cache_dir: Path | None = None,
        *,
        refresh_catalog: bool = False,
        **_: object,
    ):
        self._engine = engine
        self._catalog_url = base_url
        self._csv_path = cache_dir.resolve() / CATALOG_FILENAME if cache_dir else None
        self._refresh_catalog = refresh_catalog
        self._entries: list[UsaidDecEntry] | None = None

    def discover(self, filters: CatalogFilters) -> Iterable[WorkRef]:
        requested_formats = set(filters.formats or SUPPORTED_FORMATS)
        if not requested_formats.intersection(SUPPORTED_FORMATS):
            logger.info(
                "USAID DEC Archive only offers PDF; no requested format can be "
                "downloaded"
            )
            return []
        entries = self._load_catalog()

        downloadable = [entry for entry in entries if entry.pdf_url]
        source_book_ids = {
            str(book_id).strip()
            for book_id in filters.options.get("book_ids", [])
            if str(book_id).strip()
        }
        positions = {
            int(book_id)
            for book_id in filters.book_ids or []
            if str(book_id).strip().isdigit()
        }
        if source_book_ids:
            if filters.languages:
                logger.info(
                    "Ignoring language filters for explicitly requested USAID DEC IDs"
                )
            wanted = {book_id.casefold() for book_id in source_book_ids}
            selected = [
                entry for entry in downloadable if entry.book_id.casefold() in wanted
            ]
        elif positions:
            if filters.languages:
                logger.info(
                    "Ignoring language filters for explicitly requested USAID DEC "
                    "positions"
                )
            selected = [
                entry
                for position, entry in enumerate(downloadable, start=1)
                if position in positions
            ]
        else:
            selected = self._filter_entries(downloadable, filters)

        logger.info(
            "  Selected %s USAID DEC reports from %s catalog entries (languages: %s)",
            len(selected),
            len(entries),
            filters.languages or "all",
        )
        return [self._to_ref(entry) for entry in selected]

    @staticmethod
    def _filter_entries(
        entries: list[UsaidDecEntry], filters: CatalogFilters
    ) -> list[UsaidDecEntry]:
        if filters.languages:
            wanted = {lang.casefold() for lang in filters.languages}
            # accept ISO 639-1 and 639-3 codes interchangeably
            mapped = set(wanted)
            for lang in wanted:
                mapped.add(ISO_MATRIX.get(lang, lang))
                mapped.add(ISO_MATRIX_REV.get(lang, lang))
            entries = [
                entry
                for entry in entries
                if not entry.languages
                or any(lang.casefold() in mapped for lang in entry.languages)
            ]
        return entries

    @staticmethod
    def _to_ref(entry: UsaidDecEntry) -> WorkRef:
        return WorkRef(
            id=entry.book_id,
            source=USAIDDEC_SOURCE,
            extra={
                "title": entry.title,
                "description": entry.description,
                "languages": list(entry.languages) or ["en"],
                "authors": list(entry.authors),
                "date_published": entry.date_published,
                "pdf_url": entry.pdf_url,
                "source_url": entry.source_url,
                "file_size": entry.file_size,
                "bibtype": entry.bibtype,
                "class_name": entry.class_name,
                "subjects": list(entry.subjects),
                "geographies": list(entry.geographies),
            },
        )

    def refresh(self) -> None:
        if self._csv_path is None:
            critical_error("--refresh-catalog requires --cache-dir")
        self._entries = None
        self._load_catalog(force=True)

    def _load_catalog(self, *, force: bool = False) -> list[UsaidDecEntry]:
        if self._entries is not None and not force:
            return self._entries

        csv_text = self._read_csv_text(force=force)
        self._entries = _parse_catalog(csv_text)
        return self._entries

    def _read_csv_text(self, *, force: bool) -> str:
        if self._csv_path is None:
            logger.info("Downloading USAID DEC catalog from %s", self._catalog_url)
            return _extract_csv_from_zip(self._engine.fetch_bytes(self._catalog_url))

        if force or self._refresh_catalog or not self._csv_path.exists():
            logger.info(
                "%s USAID DEC catalog from %s",
                "Refreshing" if self._csv_path.exists() else "Downloading",
                self._catalog_url,
            )
            data = self._engine.fetch_bytes(self._catalog_url)
            csv_text = _extract_csv_from_zip(data)
            self._csv_path.write_text(csv_text, encoding="utf-8")
            return csv_text

        logger.info("Using cached USAID DEC catalog at %s", self._csv_path)
        return self._csv_path.read_text(encoding="utf-8")
