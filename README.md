# FileFerret

Ask a plain-English question; FileFerret searches the files on your PC and answers with the exact file, page, and line.

It works the way Claude Code searches a repo: a model is handed a few read-only tools
and runs a search → read → refine loop until it can answer:

- `grep_text` — search inside files; several folders in one call (`paths`), `files_only` to just list matching files
- `find_files` — search file names only
- `preview_files` — skim the opening lines of many files, for "find the story / the recipe" questions where the word isn't in the file
- `read_file`, `file_info`, `list_dir`

Every citation in the answer is checked against the real file before it's shown.

Searches inside `.txt`, `.md` and `.pdf` files; other files can be found by name. DOCX support is next.

### PDFs

- The PDF's text layer is read, page by page; citations include the page: `report.pdf:p3:L12`.
- Scanned pages and drawings (pages that are just images) have no text layer and can't be read yet.
- Extracting PDF text is slow (~25 ms per page), so it's cached in
  `%LOCALAPPDATA%\FileFerret\cache` (or `FILEFERRET_CACHE_DIR`). The first search of a big PDF
  folder takes a while (`-v` shows progress); later searches are fast. A PDF is re-read
  automatically when it changes.
- The cache holds plain-text copies of PDFs you've searched. `fileferret cache` shows its size;
  `fileferret cache --clear` deletes it.

## Install

```
pip install -e .
```

Copy `.env.example` to `.env` and fill in the API key for the provider you use:
`ANTHROPIC_API_KEY` (Claude), `OPENAI_API_KEY` (ChatGPT) or `GEMINI_API_KEY` (Gemini). `.env` is git-ignored.
For OpenAI or Gemini models also run `pip install -e ".[openai]"`. Local Ollama models need no key.

## Usage

```
fileferret ask "find me a file named trial on my desktop"
fileferret ask "Where did I write down the router password?" --root C:\Users\me\Documents
```

Add `-v` to see each tool call as it happens, and `--max-steps N` to change how many model calls it may make (default 20).

### Which folders it searches

- **Allowed folders** are searched without asking: every `--root` you pass (repeat it for several),
  else `FILEFERRET_ROOTS` in `.env` (separate several with `;`), else your user folder.
  `AppData`, `Program Files` and other system folders are always skipped.
- The model is told where your Desktop, Documents and Downloads folders are, so "on my desktop" works.
- If the model wants to look **outside** the allowed folders, you're asked once per folder:
  `Allow for this run? [y/N]`. Saying no tells the model it was denied. When nobody can answer
  (piped or scripted runs), outside access is always denied.
- With a cloud model, the contents of files it reads are sent to that provider.

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
