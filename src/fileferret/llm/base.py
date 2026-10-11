"""Provider-neutral types that every model client speaks.

The agent loop only uses these, so swapping providers never touches agent code.

Conversation history is a list of plain dicts:
    {"role": "user", "content": str}
    {"role": "assistant", "content": str, "tool_calls": [ToolCall], "raw": <provider data>}
    {"role": "tool", "tool_call_id": str, "name": str, "content": str, "is_error": bool}

Tool schemas use one canonical shape ({"name", "description", "input_schema"});
each client converts them to whatever its provider expects.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    refused: bool = False
    # Provider-native assistant content, echoed back unchanged on the next turn.
    raw: Any = None

    def to_message(self) -> dict:
        return {
            "role": "assistant",
            "content": self.text,
            "tool_calls": self.tool_calls,
            "raw": self.raw,
        }


class LLMClient(Protocol):
    model: str

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse: ...


def to_function_tool(tool: dict) -> dict:
    """Canonical tool schema -> the {"type": "function"} shape used by OpenAI and Ollama."""
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


def parse_arguments(args: Any) -> dict:
    """Tool-call arguments may arrive as a JSON string or an object; always return a dict."""
    if isinstance(args, str):
        try:
            return json.loads(args) if args else {}
        except json.JSONDecodeError:
            return {}
    return args or {}
