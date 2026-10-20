import os

import pytest

from fileferret.extractors import (
    ExtractionError, UnsupportedFileType, cache, extract, has_text, is_supported, pdf_extract,
)
from pdf_util import make_pdf


def test_text_file_is_one_page_of_lines(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("first\nsecond\n", encoding="utf-8")
    assert extract(f) == [["first", "second"]]


def test_bom_is_stripped(tmp_path):
    f = tmp_path / "a.md"
    f.write_bytes("﻿hello".encode("utf-8"))
    assert extract(f) == [["hello"]]


def test_unsupported_type_raises(tmp_path):
    f = tmp_path / "a.jpg"
    f.write_bytes(b"\xff\xd8")
    assert not is_supported(f)
    with pytest.raises(UnsupportedFileType):
        extract(f)


def test_pdf_pages_and_lines(tmp_path):
    pdf = make_pdf(tmp_path / "r.pdf", [["Title", "Intro (draft)"], ["Second page"], []])
    pages = extract(pdf)
    assert pages == [["Title", "Intro (draft)"], ["Second page"], []]
    assert has_text(pages) and not has_text([[], [" "]])


def test_corrupt_pdf_raises_extraction_error(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 garbage")
    with pytest.raises(ExtractionError, match="can't read PDF"):
        extract(bad)


@pytest.fixture
def count_reads(monkeypatch):
    """Counts how many times pypdf actually opens a file."""
    calls = []
    real = pdf_extract.PdfReader

    def counting(path, *args, **kwargs):
        calls.append(path)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(pdf_extract, "PdfReader", counting)
    return calls


def test_pdf_text_is_cached_in_memory_and_on_disk(tmp_path, count_reads):
    pdf = make_pdf(tmp_path / "r.pdf", [["cached text"]])
    first = extract(pdf)
    assert extract(pdf) == first and len(count_reads) == 1      # memory hit
    cache._memory.clear()
    assert extract(pdf) == first and len(count_reads) == 1      # disk hit, e.g. the next run
    assert cache.stats()[0] == 1


def test_changed_pdf_is_re_extracted(tmp_path, count_reads):
    pdf = make_pdf(tmp_path / "r.pdf", [["old text"]])
    extract(pdf)
    make_pdf(pdf, [["new text"]])
    stat = pdf.stat()
    os.utime(pdf, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10**9))
    assert extract(pdf) == [["new text"]] and len(count_reads) == 2


def test_broken_pdf_error_is_cached(tmp_path, count_reads):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 garbage")
    for _ in range(2):
        cache._memory.clear()
        with pytest.raises(ExtractionError):
            extract(bad)
    assert len(count_reads) == 1


def test_clear_empties_the_cache(tmp_path):
    extract(make_pdf(tmp_path / "r.pdf", [["x"]]))
    cache.clear()
    assert cache.stats() == (0, 0)


def test_on_extract_reports_only_real_extractions(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(cache, "on_extract", seen.append)
    pdf = make_pdf(tmp_path / "r.pdf", [["x"]])
    extract(pdf)
    extract(pdf)
    assert seen == [pdf.resolve()]
