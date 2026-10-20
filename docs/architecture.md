# Architecture

FileFerret is an agent loop around a few read-only tools. The model decides what to search;
the code runs the tools, keeps the model inside the allowed folders, and checks the citations.

## The loop

1. **CLI** (`cli.py`) loads `.env`, works out the allowed folders and builds the model client.
2. **Prompt** (`agent/prompts.py`): the model gets your OS, user folder, Desktop/Documents/Downloads
   paths, rules for choosing tools, the citation format, your question, and the tool definitions.
3. **Loop** (`agent/loop.py`): the model either calls tools or answers.
   - Each tool call runs and its result is appended to the conversation. Bad arguments,
     missing files or denied folders go back to the model as error messages, never crashes.
   - The full conversation is sent again on every step; the model has no memory of its own.
   - It stops when the model answers without calling a tool, refuses, or reaches `--max-steps`.
4. **Citation check** (`agent/citations.py`): every `[path:pN:L12]` in the answer is re-opened and
   the quoted lines are read from the real file. Locations that don't exist are flagged.
5. **Output**: the answer, then a Sources list with each location and its first quoted line.

## Tools

All tools are read-only and take paths relative to the first allowed folder, or absolute paths
(which may trigger an approval prompt).

| Tool | Use it for | Returns |
|---|---|---|
| `grep_text` | Names, quotes, facts and phrases inside files. Several folders per call (`paths`); `files_only` lists matching files with counts. | `path:p2:L4: line` |
| `find_files` | When the user describes a file's name, type or location. Never looks inside files. | Paths with size and date |
| `preview_files` | "Find the story / the recipe" questions where the word isn't in the file. | First lines of up to 30 files, newest first |
| `read_file` | Reading around a hit; for PDFs, one page. | Numbered lines `L12: text` |
| `file_info` | Comparing candidate files; spotting scanned PDFs. | Type, size, date, pages, lines |
| `list_dir` | Seeing what's in one folder. | Folders, then files with sizes |

When a search finds nothing, the result suggests what to try next (another tool, other wordings
or more folders). Small models follow those hints better than abstract instructions.

## Source layout

```
src/fileferret/
  cli.py            ask and cache commands, approval prompt, printing sources
  workspace.py      allowed folders, approvals, known folders
  agent/            loop, system prompt, answer and citation types, citation checking
  llm/              one client per provider behind a shared interface:
                    Anthropic, OpenAI, Gemini (OpenAI-compatible endpoint), Ollama
  tools/            one file per tool; shared walking, path and output helpers in common.py
  extractors/       files to pages of lines: text (.txt, .md), PDF, disk cache for PDF text
                    (docx_extract.py is a stub, not yet registered)
tests/              pytest; scripted fake model, generated test PDFs
```

## Extending it

- **A tool**: add `tools/<name>.py` with a `SCHEMA` (name, description, `input_schema`) and
  `run(ws, **arguments) -> str`, then add the module to `_MODULES` in `tools/__init__.py`.
  Raise `ToolError` for problems the model can fix.
- **A file type**: write `extract(path) -> list[list[str]]` (pages of lines) in `extractors/` and
  register its suffix in `_BY_SUFFIX` in `extractors/__init__.py`. Add it to `_CACHED` if it's
  slow to extract. Raise `ExtractionError` for unreadable files.
- **A provider**: write a client with `chat(system, messages, tools) -> LLMResponse` (see
  `llm/base.py` for the shared message format) and add a branch in `llm/__init__.get_client`.

## Tests

```powershell
pip install -e ".[dev]"
pytest
```

The tests replay scripted model responses, so they need no API key. They show the tools and the
loop work; they don't show how well a real model chooses tools.
