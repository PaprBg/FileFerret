"""Search inside readable files with a regex; return matching lines with their locations."""

import re
from collections.abc import Iterator
from itertools import islice
from pathlib import Path

from fileferret.extractors import extract, is_supported
from fileferret.tools.common import (
    SUPPORTED_TEXT, ToolError, clip, location, matches_glob, relative, resolve_path, walk_files,
)

MAX_HITS = 50
MAX_FILE_BYTES = 5 * 1024 * 1024

SCHEMA = {
    "name": "grep_text",
    "description": (
        f"Search inside readable files ({SUPPORTED_TEXT}) for a regular expression. "
        "Case-insensitive by default. Cover variations with alternation, "
        "e.g. 'password|passwd|pwd'. Returns lines as 'path:L12: text'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Python regular expression."},
            "path": {"type": "string", "description": "File or folder to search. Default: search root."},
            "glob": {"type": "string", "description": "Only search files matching this glob, e.g. '*.md'."},
            "case_sensitive": {"type": "boolean"},
        },
        "required": ["pattern"],
    },
}


def run(root: Path, pattern: str, path: str = ".", glob: str | None = None,
        case_sensitive: bool = False) -> str:
    try:
        regex = re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)
    except re.error as e:
        raise ToolError(f"invalid regex {pattern!r}: {e}") from None

    start = resolve_path(root, path)
    hits = list(islice(_hits(root, start, regex, glob), MAX_HITS + 1))
    if not hits:
        return f"No matches for {pattern!r}."
    if len(hits) > MAX_HITS:
        hits[MAX_HITS:] = [f"... more matches not shown; use a narrower pattern, path, or glob."]
    return "\n".join(hits)


def _hits(root: Path, start: Path, regex: re.Pattern, glob: str | None) -> Iterator[str]:
    for file in walk_files(start):
        rel = relative(root, file)
        if not is_supported(file) or (glob and not matches_glob(rel, glob)):
            continue
        try:
            if file.stat().st_size > MAX_FILE_BYTES:
                continue
            pages = extract(file)
        except OSError:
            continue
        for page_no, lines in enumerate(pages, 1):
            for line_no, line in enumerate(lines, 1):
                if regex.search(line):
                    yield f"{location(rel, page_no, len(pages), line_no)}: {clip(line.strip())}"
