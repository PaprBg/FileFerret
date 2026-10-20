# Models and providers

FileFerret works with four model providers. The model does all the searching decisions, so the
choice of model matters more than anything else for answer quality.

| Provider | `--provider` | Default model | Cost | Your files go to | Install |
|---|---|---|---|---|---|
| Claude | `anthropic` | `claude-opus-5-5` | Paid API key | Anthropic | `pip install -e .` |
| ChatGPT | `openai` | `gpt-5` | Paid API key | OpenAI | `pip install -e ".[openai]"` |
| Gemini | `gemini` | `gemini-3.6-flash` | Free tier available | Google | `pip install -e ".[gemini]"` |
| Ollama (local) | `ollama` | `llama3.1` | Free | Nowhere, stays on your PC | Install [Ollama](https://ollama.com) |

## Setting it up

Put your choice and key in `.env` (copied from `.env.example`; it's git-ignored):

```
FILEFERRET_PROVIDER=gemini
FILEFERRET_MODEL=gemini-3.5-flash     # empty = the provider's default model
GEMINI_API_KEY=...
```

| Provider | Key in `.env` |
|---|---|
| Claude | `ANTHROPIC_API_KEY` |
| ChatGPT | `OPENAI_API_KEY` (optionally `OPENAI_BASE_URL` for LM Studio, vLLM or other OpenAI-compatible servers) |
| Gemini | `GEMINI_API_KEY`, from [Google AI Studio](https://aistudio.google.com) |
| Ollama | none; `OLLAMA_HOST` if it isn't at `http://localhost:11434` |

Override per question with `--provider` and `--model`:

```powershell
fileferret ask "..." --provider gemini --model gemini-3.5-flash
fileferret ask "..." --provider ollama --model qwen3:8b
```

## Which models work well

Answers come from the model choosing good searches, so weaker models fail in visible ways:

- **gemini-3.5-flash** found a story by a character's name across several folders and cited it
  correctly. **gemini-3.5-flash-lite** only searched file names on the same question and gave up.
- **phi4-mini** (3.8B, local) sometimes wrote its tool calls as plain text instead of calling
  them, which ends the run with nothing searched.
- Claude and GPT models are the most reliable at choosing tools.

For local models, pick one that supports tool calling and fits in your free memory; a 3.8B
model needs about 3 GB free. `ollama show <model>` lists `tools` under Capabilities when it
supports them.

## Free-tier limits (Gemini)

- About **5 requests a minute and 20 a day per model**. Each loop step is one request, and a
  question usually takes 3–7.
- Limits are counted per model, so when one runs out you can switch with `--model`.
- On a per-minute limit or a "high demand" error, FileFerret waits and retries (up to 4 times,
  printing how long it's waiting). On a daily limit it stops and tells you when it resets.
- Free-tier prompts, including file snippets FileFerret reads, may be used by Google to improve
  its products.
