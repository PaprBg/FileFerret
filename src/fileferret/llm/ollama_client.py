"""Local models served by Ollama (https://ollama.com). Files never leave your PC.

Start Ollama and pull a model that supports tool calling, e.g. `ollama pull llama3.1`.
"""

import json
import urllib.error
import urllib.request

from fileferret.llm.base import LLMResponse, ToolCall, parse_arguments, to_function_tool

DEFAULT_MODEL = "llama3.1"
DEFAULT_HOST = "http://localhost:11434"


class OllamaClient:
    def __init__(self, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST):
        self.model = model
        self.host = host.rstrip("/")

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        body = {
            "model": self.model,
            "stream": False,
            "messages": [{"role": "system", "content": system}, *_to_ollama(messages)],
            "tools": [to_function_tool(t) for t in tools],
        }
        request = urllib.request.Request(
            f"{self.host}/api/chat",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=600) as resp:
                msg = json.load(resp)["message"]
        except urllib.error.HTTPError as e:
            # Ollama explains failures (model not pulled, not enough memory) in the body.
            detail = e.read().decode(errors="replace")
            try:
                detail = json.loads(detail)["error"]
            except (ValueError, KeyError):
                pass
            raise RuntimeError(f"Ollama error ({e.code}): {detail}") from None
        except urllib.error.URLError as e:
            raise RuntimeError(f"Can't reach Ollama at {self.host}; is it running? ({e.reason})") from None

        calls = [
            ToolCall(f"call_{i}", c["function"]["name"], parse_arguments(c["function"].get("arguments")))
            for i, c in enumerate(msg.get("tool_calls") or [])
        ]
        return LLMResponse(text=msg.get("content", ""), tool_calls=calls, raw=msg)


def _to_ollama(messages: list[dict]) -> list[dict]:
    out: list[dict] = []
    for m in messages:
        if m["role"] == "user":
            out.append({"role": "user", "content": m["content"]})
        elif m["role"] == "assistant":
            out.append(m.get("raw") or {
                "role": "assistant",
                "content": m["content"],
                "tool_calls": [
                    {"function": {"name": c.name, "arguments": c.arguments}}
                    for c in m.get("tool_calls", [])
                ],
            })
        elif m["role"] == "tool":
            out.append({"role": "tool", "tool_name": m["name"], "content": m["content"]})
    return out
