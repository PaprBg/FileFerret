"""Find files by name: a glob pattern, keywords, or both."""

import re
from pathlib import Path

from fileferret.tools.common import (
    ToolError, describe_mtime, describe_size, matches_glob, relative, resolve_path, walk_files,
)

MAX_RESULTS = 50

SCHEMA = {
    "name": "find_files",
    "description": (
        "Find files by name. Use a glob pattern (e.g. '*.md', 'notes/**/*.txt') and/or keywords "
        "that appear in the file or folder name (e.g. ['resume', 'cv']). Files whose paths match "
        "more keywords are listed first. Returns paths with size and modified date."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern, case-insensitive."},
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Words to look for in file/folder names, case-insensitive.",
            },
            "path": {"type": "string", "description": "Folder to search in. Default: search root."},
        },
    },
}


def run(root: Path, pattern: str | None = None, keywords: list[str] | str | None = None,
        path: str = ".") -> str:
    if isinstance(keywords, str):
        keywords = re.split(r"[\s,]+", keywords)
    keywords = [k.lower() for k in keywords or [] if k]
    if not pattern and not keywords:
        raise ToolError("give a glob pattern, keywords, or both")

    start = resolve_path(root, path)
    scored = []
    for file in walk_files(start):
        rel = relative(root, file)
        if pattern and not matches_glob(rel, pattern):
            continue
        score = sum(k in rel.lower() for k in keywords)
        if keywords and score == 0:
            continue
        scored.append((-score, rel, file))

    if not scored:
        return "No files found."
    scored.sort()
    lines = []
    for _, rel, file in scored[:MAX_RESULTS]:
        try:
            lines.append(f"{rel}  ({describe_size(file.stat().st_size)}, modified {describe_mtime(file)})")
        except OSError:
            lines.append(rel)
    if len(scored) > MAX_RESULTS:
        lines.append(f"... {len(scored) - MAX_RESULTS} more not shown; narrow the search.")
    return "\n".join(lines)
