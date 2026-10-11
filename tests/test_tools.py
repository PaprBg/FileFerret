import pytest

from fileferret.tools import SCHEMAS, TOOLS, ToolError
from fileferret.tools import file_info, find_files, grep_text, list_dir, read_file


def test_every_schema_has_a_handler():
    assert {s["name"] for s in SCHEMAS} == set(TOOLS)


def test_paths_outside_root_are_refused(docs):
    with pytest.raises(ToolError):
        read_file.run(docs, "../outside.txt")


def test_find_files_by_pattern_and_keywords(docs):
    assert "notes/wifi.md" in find_files.run(docs, pattern="*.md")
    out = find_files.run(docs, keywords=["resume"])
    assert out.startswith("resume.pdf")  # unreadable types can still be found by name
    assert "skip.txt" not in find_files.run(docs, pattern="*.txt")  # venv is skipped


def test_find_files_needs_a_query(docs):
    with pytest.raises(ToolError):
        find_files.run(docs)


def test_grep_text_finds_lines_case_insensitively(docs):
    out = grep_text.run(docs, "PASSWORD|passwd")
    assert "notes/wifi.md:L4: WiFi password: hunter2" in out
    assert "skip.txt" not in out


def test_grep_text_glob_and_no_matches(docs):
    assert "todo.txt:L2" in grep_text.run(docs, "insurance", glob="*.txt")
    assert grep_text.run(docs, "insurance", glob="*.md").startswith("No matches")


def test_grep_text_rejects_bad_regex(docs):
    with pytest.raises(ToolError):
        grep_text.run(docs, "(unclosed")


def test_read_file_returns_numbered_range(docs):
    out = read_file.run(docs, "notes/wifi.md", offset=3, limit=2)
    assert out.splitlines() == [
        "notes/wifi.md — lines 3-4 of 5",
        "L3: Router: TP-Link",
        "L4: WiFi password: hunter2",
    ]


def test_read_file_accepts_numbers_as_strings(docs):
    assert "L4:" in read_file.run(docs, "notes/wifi.md", offset="4", limit="1")


def test_read_file_unsupported_type(docs):
    with pytest.raises(ToolError, match="can't be read yet"):
        read_file.run(docs, "resume.pdf")


def test_file_info(docs):
    out = file_info.run(docs, "notes/wifi.md")
    assert "type: .md (readable)" in out and "lines: 5" in out
    assert "not readable yet" in file_info.run(docs, "resume.pdf")


def test_list_dir(docs):
    out = list_dir.run(docs).splitlines()
    assert out[0] == "notes/"
    assert any(line.startswith("todo.txt") for line in out)
