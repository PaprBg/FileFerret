"""Claude models via the Anthropic API (needs ANTHROPIC_API_KEY or `ant auth login`)."""

import anthropic

from fileferret.llm.base import LLMResponse, ToolCall

DEFAULT_MODEL = "claude-opus-5-5"

# Models that accept server-side refusal fallbacks; on a safety decline the API
# re-runs the request on a fallback model instead of stopping.
_FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}


class AnthropicClient:
    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = 16000):
        self.model = model
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic()

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        kwargs = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=_to_anthropic(messages),
            tools=tools,
        )
        if self.model in _FALLBACK_MODELS:
            response = self._client.beta.messages.create(
                betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs
            )
        else:
            response = self._client.messages.create(**kwargs)

        return LLMResponse(
            text="".join(b.text for b in response.content if b.type == "text"),
            tool_calls=[
                ToolCall(b.id, b.name, b.input) for b in response.content if b.type == "tool_use"
            ],
            refused=response.stop_reason == "refusal",
            raw=response.content,
        )


def _to_anthropic(messages: list[dict]) -> list[dict]:
    out: list[dict] = []
    for m in messages:
        if m["role"] == "user":
            out.append({"role": "user", "content": m["content"]})
        elif m["role"] == "assistant":
            # Echo the original blocks (including thinking) when we have them.
            out.append({"role": "assistant", "content": m.get("raw") or _assistant_blocks(m)})
        elif m["role"] == "tool":
            block = {
                "type": "tool_result",
                "tool_use_id": m["tool_call_id"],
                "content": m["content"],
                "is_error": m.get("is_error", False),
            }
            # All results for one assistant turn go in a single user message.
            if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                out[-1]["content"].append(block)
            else:
                out.append({"role": "user", "content": [block]})
    return out


def _assistant_blocks(m: dict) -> list[dict]:
    blocks: list[dict] = [{"type": "text", "text": m["content"]}] if m["content"] else []
    for call in m.get("tool_calls", []):
        blocks.append({"type": "tool_use", "id": call.id, "name": call.name, "input": call.arguments})
    return blocks
