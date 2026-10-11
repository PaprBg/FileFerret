"""ChatGPT / OpenAI models via the OpenAI API (needs OPENAI_API_KEY).

Install the SDK with `pip install -e ".[openai]"`. Passing `base_url` also lets this
client talk to any OpenAI-compatible server (LM Studio, vLLM, llama.cpp server, ...).
"""

import json
import re
import sys
import time

from openai import InternalServerError, OpenAI, RateLimitError

from fileferret.llm.base import LLMResponse, ToolCall, parse_arguments, to_function_tool

DEFAULT_MODEL = "gpt-5"

# Free tiers allow only a few requests per minute and get overloaded at peak times;
# wait and retry this many times on a 429 (rate limit) or 5xx (e.g. 503 high demand).
RETRIES = 4
DEFAULT_RETRY_SECONDS = 20.0
MAX_RETRY_SECONDS = 90.0


class OpenAIClient:
    def __init__(self, model: str = DEFAULT_MODEL, base_url: str | None = None,
                 api_key: str | None = None):
        self.model = model
        # None falls back to the OPENAI_API_KEY / OPENAI_BASE_URL env vars.
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def chat(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        request = dict(
            model=self.model,
            messages=[{"role": "system", "content": system}, *_to_openai(messages)],
            tools=[to_function_tool(t) for t in tools],
        )
        for attempt in range(RETRIES + 1):
            try:
                response = self._client.chat.completions.create(**request)
                break
            except (RateLimitError, InternalServerError) as e:
                wait = _retry_delay(e)
                if wait > MAX_RETRY_SECONDS:
                    # e.g. a daily quota: retrying in seconds can't help.
                    raise RuntimeError(
                        f"{self.model} quota exhausted; try again in {_describe_wait(wait)} "
                        "or switch to another model with --model"
                    ) from None
                if attempt == RETRIES:
                    raise
                reason = "rate limited" if isinstance(e, RateLimitError) else f"server error {e.status_code}"
                print(f"  ({self.model} {reason}; waiting {wait:.0f}s and retrying)", file=sys.stderr)
                time.sleep(wait)
        msg = response.choices[0].message
        calls = [
            ToolCall(c.id, c.function.name, parse_arguments(c.function.arguments))
            for c in msg.tool_calls or []
        ]
        return LLMResponse(
            text=msg.content or msg.refusal or "",
            tool_calls=calls,
            refused=msg.refusal is not None,
            # Keep the tool calls exactly as received: some servers add fields that must be
            # echoed back (Gemini puts a required thought_signature in extra_content).
            raw={"tool_calls": [c.model_dump(exclude_none=True) for c in msg.tool_calls]}
            if msg.tool_calls else None,
        )


def _retry_delay(error: RateLimitError | InternalServerError) -> float:
    """Seconds to wait: the retry-after header, or 'retry in 16.8s' / '2h2m48s' in the message."""
    header = error.response.headers.get("retry-after") if error.response is not None else None
    try:
        return float(header) + 1
    except (TypeError, ValueError):
        pass
    match = re.search(r"retry in (?:(\d+)h)?(?:(\d+)m)?([\d.]+)s", str(error), re.IGNORECASE)
    if match:
        hours, minutes, seconds = match.groups()
        return int(hours or 0) * 3600 + int(minutes or 0) * 60 + float(seconds) + 1
    return DEFAULT_RETRY_SECONDS


def _describe_wait(seconds: float) -> str:
    minutes = round(seconds / 60)
    return f"{minutes // 60}h {minutes % 60}m" if minutes >= 60 else f"{minutes}m"


def _to_openai(messages: list[dict]) -> list[dict]:
    out: list[dict] = []
    for m in messages:
        if m["role"] == "user":
            out.append({"role": "user", "content": m["content"]})
        elif m["role"] == "assistant":
            entry: dict = {"role": "assistant", "content": m["content"] or None}
            raw = m.get("raw")
            if isinstance(raw, dict) and raw.get("tool_calls"):
                entry["tool_calls"] = raw["tool_calls"]
            elif m.get("tool_calls"):
                entry["tool_calls"] = [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
                    }
                    for c in m["tool_calls"]
                ]
            out.append(entry)
        elif m["role"] == "tool":
            out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
    return out
