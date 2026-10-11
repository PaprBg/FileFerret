"""Helpers shared by the tools: path sandboxing, folder walking, and formatting."""

import os
from collections.abc import Iterator
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from fileferret.extractors import SUPPORTED_SUFFIXES

# Folders that are never worth searching and can be huge.
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".mypy_cache", ".pytest_cache", "$RECYCLE.BIN", "System Volume Information",
}

SUPPORTED_TEXT = ", ".join(SUPPORTED_SUFFIXES)

MAX_LINE_CHARS = 300


class ToolError(Exception):
    """A problem the model can fix (bad path, bad regex, ...). Sent back to it as the tool result."""


def resolve_path(root: Path, path: str = ".") -> Path:
    """Turn a model-supplied path into an absolute path, refusing anything outside root."""
    p = Path(path or ".")
    if not p.is_absolute():
        p = root / p
    p = p.resolve()
    if p != root and root not in p.parents:
        raise ToolError(f"{path} is outside the search root")
    return p


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


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


def as_int(value: Any, name: str) -> int:
    """Small models sometimes send numbers as strings; accept both."""
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ToolError(f"{name} must be a whole number, got {value!r}") from None
