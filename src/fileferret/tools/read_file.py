"""Read a range of lines (from one page) of a readable file."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fileferret.extractors import ExtractionError, UnsupportedFileType, extract
from fileferret.tools.common import PATH_HELP, SUPPORTED_TEXT, ToolError, as_int, clip

if TYPE_CHECKING:
    from fileferret.workspace import Workspace

MAX_LINES = 400

SCHEMA = {
    "name": "read_file",
    "description": (
        f"Read numbered lines from a readable file ({SUPPORTED_TEXT}). Read a narrow range around "
        "a grep hit rather than the whole file. Lines come back as 'L12: text'. For PDFs pass "
        "page: a grep hit 'report.pdf:p3:L12' means page=3, offset near 12."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": PATH_HELP},
            "offset": {"type": "integer", "description": "First line to read (1-based). Default 1."},
            "limit": {"type": "integer", "description": f"How many lines. Default 100, max {MAX_LINES}."},
            "page": {"type": "integer", "description": "Page number for multi-page files. Default 1."},
        },
        "required": ["path"],
    },
}


def run(ws: Workspace, path: str, offset: int = 1, limit: int = 100, page: int = 1) -> str:
    offset, limit, page = as_int(offset, "offset"), as_int(limit, "limit"), as_int(page, "page")
    file = ws.resolve(path)
    if not file.is_file():
        raise ToolError(f"{path} is not a file")
    rel = ws.display(file)
    try:
        pages = extract(file)
    except UnsupportedFileType as e:
        raise ToolError(f"{rel}: {e} files can't be read yet (readable: {SUPPORTED_TEXT})") from None
    except ExtractionError as e:
        raise ToolError(f"{rel}: {e}") from None

    if not 1 <= page <= len(pages):
        raise ToolError(f"{rel} has {len(pages)} page(s); there is no page {page}")
    lines = pages[page - 1]
    if not any(line.strip() for line in lines):
        if len(pages) > 1 or file.suffix.lower() == ".pdf":
            return (f"Page {page} of {rel} has no text layer (probably a scanned image); "
                    "reading scanned pages isn't supported yet.")
        return f"{rel} is empty."
    offset = max(1, offset)
    if offset > len(lines):
        raise ToolError(f"{rel} has only {len(lines)} lines")
    end = min(len(lines), offset + max(1, min(limit, MAX_LINES)) - 1)

    where = f" page {page} of {len(pages)}," if len(pages) > 1 else ""
    header = f"{rel} —{where} lines {offset}-{end} of {len(lines)}"
    body = "\n".join(f"L{n}: {clip(lines[n - 1], 2000)}" for n in range(offset, end + 1))
    return f"{header}\n{body}"
