"""Read-only tools exposed to the model.

Each tool module has a SCHEMA (sent to the model) and run(root, **arguments) -> str.
TOOLS maps each tool name to its run function; SCHEMAS holds the definitions.
"""

from fileferret.tools import file_info, find_files, grep_text, list_dir, read_file
from fileferret.tools.common import ToolError

_MODULES = [find_files, grep_text, read_file, file_info, list_dir]

TOOLS = {m.SCHEMA["name"]: m.run for m in _MODULES}
SCHEMAS = [m.SCHEMA for m in _MODULES]

__all__ = ["TOOLS", "SCHEMAS", "ToolError"]
