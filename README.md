# FileFerret

Ask a plain-English question; FileFerret searches the files on your PC and answers with the exact file, page, and line.

It works the way Claude Code searches a repo: a model is handed a few read-only tools
(`find_files`, `grep_text`, `read_file`, `file_info`, `list_dir`) and runs a search → read → refine loop until it can answer.
Every citation in the answer is checked against the real file before it's shown.

Currently searches inside `.txt` and `.md` files; other files can be found by name. PDF and DOCX support is next.

## Install

```
pip install -e .
```

Copy `.env.example` to `.env` and fill in the API key for the provider you use:
`ANTHROPIC_API_KEY` (Claude), `OPENAI_API_KEY` (ChatGPT) or `GEMINI_API_KEY` (Gemini). `.env` is git-ignored.
For OpenAI or Gemini models also run `pip install -e ".[openai]"`. Local Ollama models need no key.

## Usage

```
fileferret ask "Where did I write down the router password?" --root C:\Users\me\Documents
```

Add `-v` to see each tool call as it happens, and `--max-steps N` to change how many model calls it may make (default 20).

## Layout

- `src/fileferret/cli.py` — command-line entry point
- `src/fileferret/agent/` — the search → read → refine loop, prompts, answer/citation types
- `src/fileferret/tools/` — read-only tools exposed to the model, one per file
- `src/fileferret/extractors/` — turn txt/md/pdf/docx into text with page/line positions
- `src/fileferret/llm/` — model backends behind one interface (Claude, ChatGPT, local Ollama)
- `tests/` — pytest tests

## Choosing a model

```
fileferret ask "..." --provider anthropic --model claude-opus-5-5   # default
fileferret ask "..." --provider openai --model gpt-5                # ChatGPT models
fileferret ask "..." --provider gemini --model gemini-3.6-flash     # Gemini (free tier available)
fileferret ask "..." --provider ollama --model llama3.1             # local, files stay on your PC
```

Or set `FILEFERRET_PROVIDER` / `FILEFERRET_MODEL` in your environment.
