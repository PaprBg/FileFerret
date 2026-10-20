"""Read-only tools exposed to the model.

Each tool module has a SCHEMA (sent to the model) and run(ws, **arguments) -> str,
where ws is the fileferret.workspace.Workspace that decides which folders may be searched.
TOOLS maps each tool name to its run function; SCHEMAS holds the definitions.
"""

from fileferret.tools import file_info, find_files, grep_text, list_dir, preview_files, read_file
from fileferret.tools.common import ToolError

_MODULES = [grep_text, find_files, preview_files, read_file, file_info, list_dir]

TOOLS = {m.SCHEMA["name"]: m.run for m in _MODULES}
SCHEMAS = [m.SCHEMA for m in _MODULES]

__all__ = ["TOOLS", "SCHEMAS", "ToolError"]
