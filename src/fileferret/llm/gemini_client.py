"""Google Gemini models via Google's OpenAI-compatible endpoint (needs GEMINI_API_KEY).

Get a key at https://aistudio.google.com. The free tier covers the Flash and Flash-Lite
models, but free-tier prompts (including file snippets FileFerret reads) may be used by
Google to improve its products. Uses the OpenAI SDK: `pip install -e ".[gemini]"`.
"""

import os

from fileferret.llm.openai_client import OpenAIClient

DEFAULT_MODEL = "gemini-3.6-flash"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class GeminiClient(OpenAIClient):
    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None):
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set; add it to your .env file")
        super().__init__(model, base_url=BASE_URL, api_key=api_key)
