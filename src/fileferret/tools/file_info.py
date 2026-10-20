"""Describe a file or folder: type, size, modified date, and page/line counts if readable."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fileferret.extractors import ExtractionError, extract, has_text, is_supported
from fileferret.tools.common import (
    PATH_HELP, SUPPORTED_TEXT, ToolError, describe_mtime, describe_size,
)

if TYPE_CHECKING:
    from fileferret.workspace import Workspace

SCHEMA = {
    "name": "file_info",
    "description": (
        "Get details about a file or folder: type, size, last modified date, whether it is "
        "readable, and its page and line counts. Useful to pick between candidate files."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string", "description": PATH_HELP}},
        "required": ["path"],
    },
}


def run(ws: Workspace, path: str) -> str:
    p = ws.resolve(path)
    if not p.exists():
        raise ToolError(f"{path} does not exist")
    info = [f"path: {ws.display(p)}"]

    if p.is_dir():
        info += ["type: folder", f"modified: {describe_mtime(p)}"]
        return "\n".join(info)

    info += [f"size: {describe_size(p.stat().st_size)}", f"modified: {describe_mtime(p)}"]
    if is_supported(p):
        try:
            pages = extract(p)
        except ExtractionError as e:
            info.append(f"type: {p.suffix.lower()} (can't read: {e})")
            return "\n".join(info)
        info += [
            f"type: {p.suffix.lower()} (readable)",
            f"pages: {len(pages)}",
            f"lines: {sum(len(lines) for lines in pages)}",
        ]
        if not has_text(pages):
            info.append("text: none (no text layer; probably a scanned image)")
    else:
        info.append(f"type: {p.suffix.lower() or 'no extension'} (not readable yet; readable: {SUPPORTED_TEXT})")
    return "\n".join(info)
