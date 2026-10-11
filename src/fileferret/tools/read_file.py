"""Read a range of lines (from one page) of a readable file."""

from pathlib import Path

from fileferret.extractors import UnsupportedFileType, extract
from fileferret.tools.common import (
    SUPPORTED_TEXT, ToolError, as_int, clip, relative, resolve_path,
)

MAX_LINES = 400

SCHEMA = {
    "name": "read_file",
    "description": (
        f"Read numbered lines from a readable file ({SUPPORTED_TEXT}). Read a narrow range around "
        "a grep hit rather than the whole file. Lines come back as 'L12: text'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "offset": {"type": "integer", "description": "First line to read (1-based). Default 1."},
            "limit": {"type": "integer", "description": f"How many lines. Default 100, max {MAX_LINES}."},
            "page": {"type": "integer", "description": "Page number for multi-page files. Default 1."},
        },
        "required": ["path"],
    },
}


def run(root: Path, path: str, offset: int = 1, limit: int = 100, page: int = 1) -> str:
    offset, limit, page = as_int(offset, "offset"), as_int(limit, "limit"), as_int(page, "page")
    file = resolve_path(root, path)
    if not file.is_file():
        raise ToolError(f"{path} is not a file")
    rel = relative(root, file)
    try:
        pages = extract(file)
    except UnsupportedFileType as e:
        raise ToolError(f"{rel}: {e} files can't be read yet (readable: {SUPPORTED_TEXT})") from None

    if not 1 <= page <= len(pages):
        raise ToolError(f"{rel} has {len(pages)} page(s); there is no page {page}")
    lines = pages[page - 1]
    if not lines:
        return f"{rel} is empty."
    offset = max(1, offset)
    if offset > len(lines):
        raise ToolError(f"{rel} has only {len(lines)} lines")
    end = min(len(lines), offset + max(1, min(limit, MAX_LINES)) - 1)

    where = f" page {page} of {len(pages)}," if len(pages) > 1 else ""
    header = f"{rel} —{where} lines {offset}-{end} of {len(lines)}"
    body = "\n".join(f"L{n}: {clip(lines[n - 1], 2000)}" for n in range(offset, end + 1))
    return f"{header}\n{body}"
