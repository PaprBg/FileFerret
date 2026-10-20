"""Find files by NAME: a glob pattern, keywords, or both. Never looks inside files."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from fileferret.tools.common import (
    PATH_HELP, PATHS_SCHEMA, describe_mtime, describe_size, matches_any_glob, resolve_targets,
    split_list, walk_targets,
)

if TYPE_CHECKING:
    from fileferret.workspace import Workspace

MAX_RESULTS = 50

NO_MATCH_HINT = (
    "No file names match. File names often don't mention the topic: use grep_text to search "
    "inside files, or preview_files to skim candidate files."
)

SCHEMA = {
    "name": "find_files",
    "description": (
        "Find files by NAME only; it never looks inside files. Use it when the user describes a "
        "file's name, type or location. Give a glob pattern (e.g. '*.md', 'notes/**/*.txt') and/or "
        "keywords that appear in the file or folder name (e.g. ['resume', 'cv']); with neither it "
        "lists all files. Files matching more keywords come first. Returns paths with size and "
        "modified date."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern(s), case-insensitive, comma-separated."},
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Words to look for in file/folder names, case-insensitive.",
            },
            "path": {"type": "string", "description": f"Folder to search in. {PATH_HELP}"},
            "paths": PATHS_SCHEMA,
        },
    },
}


def run(ws: Workspace, pattern: Any = None, keywords: Any = None, path: str | None = None,
        paths: Any = None) -> str:
    if isinstance(keywords, str):
        keywords = re.split(r"[\s,]+", keywords)
    globs = split_list(pattern)
    words = []
    for k in keywords or []:
        k = str(k).strip().lower()
        # A keyword with wildcards ('*', 'story*') is meant as a name glob, not literal text.
        if "*" in k or "?" in k:
            globs.append(k)
        elif k:
            words.append(k)

    scored = []
    for file in walk_targets(resolve_targets(ws, path, paths)):
        rel = ws.display(file)
        if globs and not matches_any_glob(rel, globs):
            continue
        score = sum(w in rel.lower() for w in words)
        if words and score == 0:
            continue
        scored.append((-score, rel, file))

    if not scored:
        return NO_MATCH_HINT
    scored.sort()
    lines = []
    for _, rel, file in scored[:MAX_RESULTS]:
        try:
            lines.append(f"{rel}  ({describe_size(file.stat().st_size)}, modified {describe_mtime(file)})")
        except OSError:
            lines.append(rel)
    if len(scored) > MAX_RESULTS:
        lines.append(f"... {len(scored) - MAX_RESULTS} more not shown; narrow with pattern, keywords or paths.")
    return "\n".join(lines)
