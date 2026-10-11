import pytest

from fileferret.llm import get_client
from fileferret.llm.base import LLMResponse, ToolCall, parse_arguments, to_function_tool
from fileferret.llm.ollama_client import OllamaClient
from fileferret.tools import SCHEMAS


def test_get_client_picks_provider_and_model():
    client = get_client("ollama", "qwen3")
    assert isinstance(client, OllamaClient)
    assert client.model == "qwen3"


def test_get_client_rejects_unknown_provider():
    with pytest.raises(ValueError):
        get_client("nope")


def test_tool_schemas_convert_to_function_shape():
    converted = to_function_tool(SCHEMAS[0])
    assert converted["function"]["name"] == SCHEMAS[0]["name"]
    assert converted["function"]["parameters"] == SCHEMAS[0]["input_schema"]


def test_parse_arguments_accepts_string_or_dict():
    assert parse_arguments('{"pattern": "x"}') == {"pattern": "x"}
    assert parse_arguments({"pattern": "x"}) == {"pattern": "x"}
    assert parse_arguments("not json") == {}


def test_openai_message_conversion():
    openai_client = pytest.importorskip("fileferret.llm.openai_client")
    reply = LLMResponse("", [ToolCall("call_1", "grep_files", {"pattern": "x"})])
    out = openai_client._to_openai([
        {"role": "user", "content": "q"},
        reply.to_message(),
        {"role": "tool", "tool_call_id": "call_1", "name": "grep_files", "content": "hit"},
    ])
    assert out[1]["tool_calls"][0]["function"]["arguments"] == '{"pattern": "x"}'
    assert out[2] == {"role": "tool", "tool_call_id": "call_1", "content": "hit"}


def test_openai_echoes_raw_tool_calls_unchanged():
    # Gemini rejects the next request unless extra_content.google.thought_signature comes back.
    openai_client = pytest.importorskip("fileferret.llm.openai_client")
    raw_call = {
        "id": "call_1",
        "type": "function",
        "function": {"name": "grep_text", "arguments": '{"pattern": "x"}'},
        "extra_content": {"google": {"thought_signature": "sig123"}},
    }
    reply = LLMResponse("", [ToolCall("call_1", "grep_text", {"pattern": "x"})],
                        raw={"tool_calls": [raw_call]})
    [assistant] = openai_client._to_openai([reply.to_message()])
    assert assistant["tool_calls"] == [raw_call]


def test_retry_delay_parses_short_and_long_waits():
    openai_client = pytest.importorskip("fileferret.llm.openai_client")

    class FakeError(Exception):
        response = None

    assert openai_client._retry_delay(FakeError("Please retry in 16.5s.")) == 17.5
    assert openai_client._retry_delay(FakeError("Please retry in 2h2m48.5s.")) == 7369.5
    assert openai_client._retry_delay(FakeError("no hint")) == openai_client.DEFAULT_RETRY_SECONDS


def test_gemini_needs_a_key(monkeypatch):
    pytest.importorskip("openai")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        get_client("gemini")
