"""List the files and folders directly inside a folder."""

from pathlib import Path

from fileferret.tools.common import ToolError, describe_size, resolve_path

MAX_ENTRIES = 200

SCHEMA = {
    "name": "list_dir",
    "description": "List files and folders directly inside a folder. Folders end with '/'.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Folder to list. Default: search root."},
        },
    },
}


def run(root: Path, path: str = ".") -> str:
    folder = resolve_path(root, path)
    if not folder.is_dir():
        raise ToolError(f"{path} is not a folder")
    try:
        entries = sorted(folder.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        raise ToolError(f"no permission to list {path}") from None

    if not entries:
        return "(empty folder)"
    lines = [_describe(e) for e in entries[:MAX_ENTRIES]]
    if len(entries) > MAX_ENTRIES:
        lines.append(f"... {len(entries) - MAX_ENTRIES} more not shown.")
    return "\n".join(lines)


def _describe(entry: Path) -> str:
    if entry.is_dir():
        return f"{entry.name}/"
    try:
        return f"{entry.name}  ({describe_size(entry.stat().st_size)})"
    except OSError:
        return entry.name
