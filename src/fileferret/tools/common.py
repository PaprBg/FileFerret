"""Helpers shared by the tools: folder walking and formatting.

Path resolution and the allowed-folder check live in fileferret.workspace.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fileferret.extractors import SUPPORTED_SUFFIXES, is_supported, max_bytes

if TYPE_CHECKING:
    from fileferret.workspace import Workspace

# Folders that are never worth searching and can be huge: tooling caches, plus Windows
# system and program-data folders (the default root is the user folder, which holds AppData).
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".mypy_cache", ".pytest_cache", "$RECYCLE.BIN", "System Volume Information",
    "AppData", "Application Data", "Local Settings", "Program Files", "Program Files (x86)",
    "ProgramData", "Windows",
}

SUPPORTED_TEXT = ", ".join(SUPPORTED_SUFFIXES)

# Shared description for every tool's `path` argument.
PATH_HELP = (
    "Relative to the search root (default '.'), or an absolute path. "
    "Folders outside the allowed folders need the user's approval, which the tool asks for."
)

# Shared schema for the `paths` argument: search several folders in one call.
PATHS_SCHEMA = {
    "type": "array",
    "items": {"type": "string"},
    "description": "Several files or folders to search in one call, e.g. "
                   "['Desktop', 'Documents', 'Downloads']. Combined with path if both are given.",
}

MAX_LINE_CHARS = 300


class ToolError(Exception):
    """A problem the model can fix (bad path, bad regex, ...). Sent back to it as the tool result."""


def split_list(value: Any) -> list[str]:
    """A list, or a comma-separated string (small models send both shapes)."""
    if value is None:
        return []
    items = value.split(",") if isinstance(value, str) else value
    return [str(v).strip() for v in items if str(v).strip()]


def resolve_targets(ws: Workspace, path: str | None = None, paths: Any = None) -> list[Path]:
    """Resolve `path` plus `paths` (each may trigger an approval prompt). Default: the root."""
    names = ([path] if path else []) + split_list(paths)
    targets: list[Path] = []
    for name in names or ["."]:
        target = ws.resolve(name)
        if target not in targets:
            targets.append(target)
    return targets


def walk_targets(targets: Iterable[Path]) -> Iterator[Path]:
    """walk_files over several targets, yielding each file once even if targets overlap."""
    seen: set[Path] = set()
    for target in targets:
        for file in walk_files(target):
            if file not in seen:
                seen.add(file)
                yield file


def readable_files(ws: Workspace, targets: Iterable[Path],
                   globs: list[str]) -> Iterator[tuple[Path, str]]:
    """(file, display path) for files an extractor can read, matching globs, not too big."""
    for file in walk_targets(targets):
        if not is_supported(file):
            continue
        rel = ws.display(file)
        if globs and not matches_any_glob(rel, globs):
            continue
        try:
            if file.stat().st_size > max_bytes(file):
                continue
        except OSError:
            continue
        yield file, rel


def walk_files(start: Path) -> Iterator[Path]:
    """Yield every file under start (or start itself if it's a file), skipping junk folders."""
    if start.is_file():
        yield start
        return
    for dirpath, dirnames, filenames in os.walk(start):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            yield Path(dirpath) / name


def matches_glob(rel: str, pattern: str) -> bool:
    """Case-insensitive glob. Patterns without '/' match the file name at any depth."""
    rel, pattern = rel.lower(), pattern.replace("\\", "/").lower()
    if "/" not in pattern:
        return fnmatch(rel.rsplit("/", 1)[-1], pattern)
    return fnmatch(rel, pattern) or (pattern.startswith("**/") and fnmatch(rel, pattern[3:]))


def matches_any_glob(rel: str, globs: list[str]) -> bool:
    return any(matches_glob(rel, g) for g in globs)


def location(rel: str, page: int, n_pages: int, line: int) -> str:
    """Citation-style location: path:L12, or path:p3:L12 for multi-page files."""
    return f"{rel}:p{page}:L{line}" if n_pages > 1 else f"{rel}:L{line}"


def clip(text: str, limit: int = MAX_LINE_CHARS) -> str:
    return text if len(text) <= limit else text[:limit] + " …"


def describe_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n} B"


def describe_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def as_bool(value: Any) -> bool:
    """Small models sometimes send booleans as strings ("true"); accept both."""
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return bool(value)


def as_int(value: Any, name: str) -> int:
    """Small models sometimes send numbers as strings; accept both."""
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ToolError(f"{name} must be a whole number, got {value!r}") from None
