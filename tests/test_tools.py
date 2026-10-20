import pytest

from fileferret.tools import SCHEMAS, TOOLS, ToolError
from fileferret.tools import file_info, find_files, grep_text, list_dir, preview_files, read_file

STORY = "Downloads/The_Lighthouse_Keepers_Last_Lantern.txt"


def test_every_schema_has_a_handler():
    assert {s["name"] for s in SCHEMAS} == set(TOOLS)


def test_paths_outside_root_are_refused(docs, outside):
    with pytest.raises(ToolError, match="outside the allowed folders"):
        read_file.run(docs, "../outside/secret.md")


def test_find_files_by_pattern_and_keywords(docs):
    assert "notes/wifi.md" in find_files.run(docs, pattern="*.md")
    out = find_files.run(docs, keywords=["resume"])
    assert out.startswith("resume.pdf")  # unreadable types can still be found by name
    assert "skip.txt" not in find_files.run(docs, pattern="*.txt")  # venv is skipped


def test_find_files_without_query_or_with_star_lists_files(docs):
    # flash-lite tried find_files(path=...) and keywords=['*'] to mean "all files"
    for out in (find_files.run(docs), find_files.run(docs, keywords=["*"])):
        assert "todo.txt" in out and STORY in out


def test_find_files_searches_names_only_and_hints_at_grep(docs):
    # The trap from the real failure: the name is inside the file, not in its file name.
    out = find_files.run(docs, keywords=["Marguerite"], paths=["Desktop", "Downloads"])
    assert out.startswith("No file names match") and "grep_text" in out


def test_grep_text_finds_lines_case_insensitively(docs):
    out = grep_text.run(docs, "PASSWORD|passwd")
    assert "notes/wifi.md:L4: WiFi password: hunter2" in out
    assert "skip.txt" not in out and "cache.txt" not in out  # venv and AppData are skipped


def test_grep_text_glob_and_no_matches(docs):
    assert "todo.txt:L2" in grep_text.run(docs, "insurance", glob="*.txt")
    assert grep_text.run(docs, "insurance", glob="*.md").startswith("No matches")


def test_grep_text_several_folders_files_only(docs):
    # One call does what took flash 4 calls: search several folders, list matching files.
    out = grep_text.run(docs, "Marguerite", paths=["Desktop", "Downloads"], files_only=True)
    assert out.splitlines() == [
        "Desktop/lexicon.txt  (1 matching line)",
        f"{STORY}  (3 matching lines)",
    ]
    # small models send paths as one comma-separated string and booleans as strings
    assert grep_text.run(docs, "Marguerite", paths="Desktop, Downloads", files_only="true") == out


def test_grep_text_multiple_globs(docs):
    out = grep_text.run(docs, "password|insurance", glob="*.md,todo.*", files_only=True)
    assert "notes/wifi.md" in out and "todo.txt" in out


def test_grep_text_no_match_hint(docs):
    out = grep_text.run(docs, "zebra", paths=["Desktop", "Downloads"])
    assert "in Desktop, Downloads" in out and "preview_files" in out


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
        read_file.run(docs, "photo.jpg")


def test_file_info(docs):
    out = file_info.run(docs, "notes/wifi.md")
    assert "type: .md (readable)" in out and "lines: 5" in out
    assert "not readable yet" in file_info.run(docs, "photo.jpg")


# --- PDFs -----------------------------------------------------------------------------------

def test_grep_text_finds_pdf_lines_with_page(docs):
    out = grep_text.run(docs, "revenue")
    assert out == "docs/report.pdf:p2:L1: Quarterly revenue grew 12%"
    # the corrupt resume.pdf is skipped rather than failing the search
    assert "docs/report.pdf  (1 matching line)" in grep_text.run(docs, "revenue", files_only=True)


def test_read_file_pdf_page(docs):
    assert read_file.run(docs, "docs/report.pdf", page=2).splitlines() == [
        "docs/report.pdf — page 2 of 2, lines 1-2 of 2",
        "L1: Quarterly revenue grew 12%",
        "L2: Costs fell slightly",
    ]


def test_read_file_pdf_without_text_layer(docs):
    assert "has no text layer" in read_file.run(docs, "docs/scan.pdf")


def test_read_file_corrupt_pdf(docs):
    with pytest.raises(ToolError, match="can't read PDF"):
        read_file.run(docs, "resume.pdf")


def test_preview_files_pdf_labels_pages(docs):
    out = preview_files.run(docs, path="docs", lines=3)
    assert "docs/report.pdf  (4 lines, 2 pages)\n  p1:L1: Annual Report 2026\n" in out
    assert "  p2:L1: Quarterly revenue grew 12%" in out
    assert "docs/scan.pdf  (0 lines)\n  (no text layer)" in out


def test_file_info_pdf(docs):
    out = file_info.run(docs, "docs/report.pdf")
    assert "type: .pdf (readable)" in out and "pages: 2" in out and "text: none" not in out
    assert "text: none" in file_info.run(docs, "docs/scan.pdf")
    assert "can't read" in file_info.run(docs, "resume.pdf")


def test_preview_files_shows_opening_lines(docs):
    # The other real failure: "a story" never appears, but the opening lines give it away.
    out = preview_files.run(docs, path="Downloads", lines=2)
    assert out.splitlines() == [
        f"{STORY}  (7 lines)",
        "  L1: THE LIGHTHOUSE KEEPER'S LAST LANTERN",
        "  L3: On the far edge of a windswept cape stood a lighthouse. Its keeper was Marguerite.",
    ]


def test_preview_files_glob_skips_unreadable_and_caps(docs, monkeypatch):
    out = preview_files.run(docs, glob="*.md,*.txt")
    assert "notes/wifi.md" in out and "resume.pdf" not in out
    monkeypatch.setattr(preview_files, "MAX_PREVIEW_FILES", 1)
    assert "more files not shown" in preview_files.run(docs)


def test_preview_files_empty_folder(docs):
    (docs.base / "empty").mkdir()
    assert preview_files.run(docs, path="empty").startswith("No readable")


def test_list_dir(docs):
    out = list_dir.run(docs).splitlines()
    todo = next(i for i, line in enumerate(out) if line.startswith("todo.txt"))
    assert out.index("notes/") < todo  # folders are listed before files
