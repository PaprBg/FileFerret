"""Skim the opening lines of many readable files at once, to judge what each file is."""

from __future__ import annotations

from collections.abc import Iterator
from itertools import islice
from typing import TYPE_CHECKING, Any

from fileferret.extractors import ExtractionError, extract
from fileferret.tools.common import (
    PATH_HELP, PATHS_SCHEMA, SUPPORTED_TEXT, as_int, clip, readable_files, resolve_targets,
    split_list,
)

if TYPE_CHECKING:
    from fileferret.workspace import Workspace

MAX_PREVIEW_FILES = 30
MAX_PREVIEW_LINES = 20
PREVIEW_LINE_CHARS = 200

SCHEMA = {
    "name": "preview_files",
    "description": (
        f"Show the first few non-empty lines of many readable files ({SUPPORTED_TEXT}) at once, "
        "most recently modified first. Use it to judge what each file is (a story, a letter, a "
        "recipe, notes, a list...) when the topic word may not appear in the file's name or text. "
        f"Shows up to {MAX_PREVIEW_FILES} files; narrow with paths or glob."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": f"File or folder to preview. {PATH_HELP}"},
            "paths": PATHS_SCHEMA,
            "glob": {
                "type": "string",
                "description": "Only preview files matching these globs, comma-separated, e.g. '*.txt'.",
            },
            "lines": {
                "type": "integer",
                "description": f"Non-empty lines to show per file. Default 5, max {MAX_PREVIEW_LINES}.",
            },
        },
    },
}


def run(ws: Workspace, path: str | None = None, paths: Any = None, glob: Any = None,
        lines: Any = 5) -> str:
    per_file = max(1, min(as_int(lines, "lines"), MAX_PREVIEW_LINES))
    targets = resolve_targets(ws, path, paths)

    candidates = []
    for file, rel in readable_files(ws, targets, split_list(glob)):
        try:
            candidates.append((-file.stat().st_mtime, rel, file))
        except OSError:
            continue
    if not candidates:
        where = ", ".join(ws.display(t) for t in targets)
        return f"No readable ({SUPPORTED_TEXT}) files in {where}."
    candidates.sort()

    blocks = []
    for _, rel, file in candidates[:MAX_PREVIEW_FILES]:
        try:
            pages = extract(file)
        except (OSError, ExtractionError):
            continue
        total = sum(len(p) for p in pages)
        where = f", {len(pages)} pages" if len(pages) > 1 else ""
        body = [f"  {label}: {clip(text.strip(), PREVIEW_LINE_CHARS)}"
                for label, text in islice(_opening_lines(pages), per_file)]
        empty = "  (no text layer)" if file.suffix.lower() == ".pdf" else "  (empty)"
        blocks.append("\n".join([f"{rel}  ({total} lines{where})", *(body or [empty])]))

    if len(candidates) > MAX_PREVIEW_FILES:
        blocks.append(f"... {len(candidates) - MAX_PREVIEW_FILES} more files not shown; "
                      "narrow with paths or glob.")
    return "\n\n".join(blocks)


def _opening_lines(pages: list[list[str]]) -> Iterator[tuple[str, str]]:
    """(label, text) for non-empty lines in reading order; labels are p2:L4 for multi-page files."""
    for page_no, lines in enumerate(pages, 1):
        for line_no, text in enumerate(lines, 1):
            if text.strip():
                yield (f"p{page_no}:L{line_no}" if len(pages) > 1 else f"L{line_no}"), text
