"""Describe a file or folder: type, size, modified date, and page/line counts if readable."""

from pathlib import Path

from fileferret.extractors import extract, is_supported
from fileferret.tools.common import (
    SUPPORTED_TEXT, ToolError, describe_mtime, describe_size, relative, resolve_path,
)

SCHEMA = {
    "name": "file_info",
    "description": (
        "Get details about a file or folder: type, size, last modified date, whether it is "
        "readable, and its page and line counts. Useful to pick between candidate files."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
}


def run(root: Path, path: str) -> str:
    p = resolve_path(root, path)
    if not p.exists():
        raise ToolError(f"{path} does not exist")
    info = [f"path: {relative(root, p) or '.'}"]

    if p.is_dir():
        info += ["type: folder", f"modified: {describe_mtime(p)}"]
        return "\n".join(info)

    info += [f"size: {describe_size(p.stat().st_size)}", f"modified: {describe_mtime(p)}"]
    if is_supported(p):
        pages = extract(p)
        info += [
            f"type: {p.suffix.lower()} (readable)",
            f"pages: {len(pages)}",
            f"lines: {sum(len(lines) for lines in pages)}",
        ]
    else:
        info.append(f"type: {p.suffix.lower() or 'no extension'} (not readable yet; readable: {SUPPORTED_TEXT})")
    return "\n".join(info)
