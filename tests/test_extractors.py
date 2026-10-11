import pytest

from fileferret.extractors import UnsupportedFileType, extract, is_supported


def test_text_file_is_one_page_of_lines(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("first\nsecond\n", encoding="utf-8")
    assert extract(f) == [["first", "second"]]


def test_bom_is_stripped(tmp_path):
    f = tmp_path / "a.md"
    f.write_bytes("﻿hello".encode("utf-8"))
    assert extract(f) == [["hello"]]


def test_unsupported_type_raises(tmp_path):
    f = tmp_path / "a.pdf"
    f.write_bytes(b"%PDF")
    assert not is_supported(f)
    with pytest.raises(UnsupportedFileType):
        extract(f)
