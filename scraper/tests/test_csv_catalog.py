import gzip

from papers2zim.sources.gutenberg.catalog import (
    CatalogEntry,
    collapse_literature_shelf,
    filter_books,
    load_catalog,
    transform_locc_code,
)

CSV_CONTENT = """Text#,Type,Language,LoCC
84,Text,en,PR
11,Text,en;fr,PS
1089,Text,fr,QA
notanumber,Text,en,H
"""

MIXED_TYPES_CONTENT = """Text#,Type,Language,LoCC
84,Text,en,PR
10137,Sound,en,
21139,Sound,en,PZ
50,Dataset,en,PZ
4749,Image,en,PZ
116,MovingImage,en,PS
"""

UNTYPED_CONTENT = """Text#,Type,Language,LoCC
84,Text,en,PR
51563,,en,PZ
"""

NO_TYPE_COLUMN_CONTENT = """Text#,Language,LoCC
84,en,PR
10137,en,
"""


def _write_catalog(tmp_path, content: str = CSV_CONTENT):
    csv_path = tmp_path / "pg_catalog.csv.gz"
    with gzip.open(csv_path, "wt", encoding="utf-8") as f:
        f.write(content)
    return csv_path


def test_load_catalog(tmp_path):
    catalog = load_catalog(_write_catalog(tmp_path))
    # the invalid book ID row is skipped
    assert len(catalog) == 3
    entry = next(e for e in catalog if e.book_id == 11)
    assert entry.languages == ["en", "fr"]
    assert entry.lcc_shelf == "PS"


def test_load_catalog_keeps_only_texts(tmp_path):
    catalog = load_catalog(_write_catalog(tmp_path, MIXED_TYPES_CONTENT))

    assert [entry.book_id for entry in catalog] == [84]


def test_load_catalog_keeps_entries_with_no_type_declared(tmp_path):
    catalog = load_catalog(_write_catalog(tmp_path, UNTYPED_CONTENT))

    assert [entry.book_id for entry in catalog] == [84, 51563]


def test_load_catalog_keeps_everything_when_the_dump_has_no_type_column(tmp_path):
    catalog = load_catalog(_write_catalog(tmp_path, NO_TYPE_COLUMN_CONTENT))

    assert [entry.book_id for entry in catalog] == [84, 10137]


def test_filter_books_no_filter():
    catalog: list[CatalogEntry] = [
        CatalogEntry(book_id=84, languages=["en"], lcc_shelf="PR"),
        CatalogEntry(book_id=11, languages=["en", "fr"], lcc_shelf="PS"),
        CatalogEntry(book_id=1089, languages=["fr"], lcc_shelf="QA"),
    ]
    assert len(filter_books(catalog)) == 3


def test_filter_books_by_language(tmp_path):
    catalog = load_catalog(_write_catalog(tmp_path))
    filtered = filter_books(catalog, languages=["fr"])
    assert {e.book_id for e in filtered} == {11, 1089}


def test_filter_books_by_ids(tmp_path):
    catalog = load_catalog(_write_catalog(tmp_path))
    filtered = filter_books(catalog, only_books=[84])
    assert [e.book_id for e in filtered] == [84]


def test_filter_books_by_lcc_shelves(tmp_path):
    catalog = load_catalog(_write_catalog(tmp_path))
    filtered = filter_books(catalog, lcc_shelves=["PR"])
    assert [e.book_id for e in filtered] == [84]


def test_transform_locc_code():
    assert transform_locc_code("PR") == "PR"
    assert transform_locc_code("QA") == "Q"
    assert transform_locc_code("") == ""
    assert transform_locc_code("b123") == "B"


def test_transform_locc_code_merges_history_shelves_into_cdef():
    assert transform_locc_code("C") == "CDEF"
    assert transform_locc_code("D") == "CDEF"
    assert transform_locc_code("E") == "CDEF"
    assert transform_locc_code("F") == "CDEF"
    assert transform_locc_code("e12") == "CDEF"


def test_collapse_literature_shelf():
    assert collapse_literature_shelf("PR") == "P"
    assert collapse_literature_shelf("PS") == "P"
    assert collapse_literature_shelf("P") == "P"
    assert collapse_literature_shelf("Q") == "Q"
    assert collapse_literature_shelf("") == ""
