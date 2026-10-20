"""Search inside readable files with a regex; return matching lines (or files) with locations."""

from __future__ import annotations

import re
from collections.abc import Iterator
from itertools import islice
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fileferret.extractors import ExtractionError, extract
from fileferret.tools.common import (
    PATH_HELP, PATHS_SCHEMA, SUPPORTED_TEXT, ToolError, as_bool, clip, location, readable_files,
    resolve_targets, split_list,
)

if TYPE_CHECKING:
    from fileferret.workspace import Workspace

MAX_HITS = 50
MAX_FILES = 50

SCHEMA = {
    "name": "grep_text",
    "description": (
        f"Search INSIDE readable files ({SUPPORTED_TEXT}) for a regular expression. "
        "Names of people, quotes, facts, numbers and phrases are inside files: use this tool for "
        "them, not find_files. Case-insensitive by default. Cover variations with alternation, "
        "e.g. 'password|passwd|pwd'. Search several folders at once with paths. Returns lines as "
        "'path:L12: text', or with files_only one line per matching file with its match count."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Python regular expression."},
            "path": {"type": "string", "description": f"File or folder to search. {PATH_HELP}"},
            "paths": PATHS_SCHEMA,
            "glob": {
                "type": "string",
                "description": "Only search files matching these globs, comma-separated, e.g. '*.txt,*.md'.",
            },
            "files_only": {
                "type": "boolean",
                "description": "List matching files with match counts instead of lines. "
                               "Good first step to locate files.",
            },
            "case_sensitive": {"type": "boolean"},
        },
        "required": ["pattern"],
    },
}


def run(ws: Workspace, pattern: str, path: str | None = None, paths: Any = None,
        glob: Any = None, files_only: Any = False, case_sensitive: Any = False) -> str:
    try:
        regex = re.compile(pattern, 0 if as_bool(case_sensitive) else re.IGNORECASE)
    except re.error as e:
        raise ToolError(f"invalid regex {pattern!r}: {e}") from None

    targets = resolve_targets(ws, path, paths)
    files = readable_files(ws, targets, split_list(glob))
    if as_bool(files_only):
        results, limit, what = list(islice(_file_counts(files, regex), MAX_FILES + 1)), MAX_FILES, "files"
    else:
        results, limit, what = list(islice(_hits(files, regex), MAX_HITS + 1)), MAX_HITS, "matches"

    if not results:
        where = ", ".join(ws.display(t) for t in targets)
        return (f"No matches for {pattern!r} in {where}. Try other wordings (regex alternation), "
                "more folders via paths, or preview_files if the words may not appear in the file.")
    if len(results) > limit:
        results[limit:] = [f"... more {what} not shown; use a narrower pattern, paths, or glob."]
    return "\n".join(results)


def _pages(file: Path) -> list[list[str]] | None:
    try:
        return extract(file)
    except (OSError, ExtractionError):  # unreadable files are skipped, not fatal
        return None


def _hits(files: Iterator[tuple[Path, str]], regex: re.Pattern) -> Iterator[str]:
    for file, rel in files:
        pages = _pages(file)
        for page_no, lines in enumerate(pages or [], 1):
            for line_no, line in enumerate(lines, 1):
                if regex.search(line):
                    yield f"{location(rel, page_no, len(pages), line_no)}: {clip(line.strip())}"


def _file_counts(files: Iterator[tuple[Path, str]], regex: re.Pattern) -> Iterator[str]:
    for file, rel in files:
        pages = _pages(file) or []
        count = sum(1 for lines in pages for line in lines if regex.search(line))
        if count:
            yield f"{rel}  ({count} matching line{'s' if count != 1 else ''})"
