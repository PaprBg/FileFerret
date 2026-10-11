"""Pick the model backend.

Choose with CLI flags (--provider / --model) or env vars (FILEFERRET_PROVIDER /
FILEFERRET_MODEL). To add a provider, write a client with a `chat()` method that
returns an LLMResponse (see base.py) and add a branch to get_client().
"""

import os

from fileferret.llm.base import LLMClient, LLMResponse, ToolCall

DEFAULT_PROVIDER = "anthropic"
PROVIDERS = ("anthropic", "openai", "gemini", "ollama")

__all__ = ["LLMClient", "LLMResponse", "ToolCall", "PROVIDERS", "get_client"]


def get_client(provider: str | None = None, model: str | None = None) -> LLMClient:
    provider = provider or os.environ.get("FILEFERRET_PROVIDER") or DEFAULT_PROVIDER
    model = model or os.environ.get("FILEFERRET_MODEL")

    # Imported lazily so you only need the SDK for the provider you use.
    if provider == "anthropic":
        from fileferret.llm.anthropic_client import DEFAULT_MODEL, AnthropicClient

        return AnthropicClient(model or DEFAULT_MODEL)
    if provider == "openai":
        from fileferret.llm.openai_client import DEFAULT_MODEL, OpenAIClient

        return OpenAIClient(model or DEFAULT_MODEL)
    if provider == "gemini":
        from fileferret.llm.gemini_client import DEFAULT_MODEL, GeminiClient

        return GeminiClient(model or DEFAULT_MODEL)
    if provider == "ollama":
        from fileferret.llm.ollama_client import DEFAULT_HOST, DEFAULT_MODEL, OllamaClient

        return OllamaClient(model or DEFAULT_MODEL, os.environ.get("OLLAMA_HOST") or DEFAULT_HOST)

    raise ValueError(f"Unknown provider {provider!r}; choose from {', '.join(PROVIDERS)}")
