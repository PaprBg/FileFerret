# Folders and privacy

## Which folders it searches

FileFerret searches a set of **allowed folders** without asking. They come from the first of
these that is set:

1. Every `--root PATH` you pass (repeat it for several folders).
2. `FILEFERRET_ROOTS` in `.env`, with several folders separated by `;`:
   `FILEFERRET_ROOTS=C:\Users\me\Documents;D:\Notes`
3. Your user folder, e.g. `C:\Users\me`.

Some folders are always skipped when searching, because they're huge and never what you want:
`AppData`, `Program Files`, `ProgramData`, `Windows`, `.git`, `node_modules`, `venv`, `.venv`,
`__pycache__`, and any folder whose name starts with a dot.

Searching your whole user folder can be slow (around 30 seconds just to list file names on a
full machine). Questions that mention a place, like "on my desktop", are much faster because the
model goes straight there. To search less by default, set `FILEFERRET_ROOTS`.

## Known folders

The model is told where your Desktop, Documents and Downloads folders are (including
OneDrive-synced copies), so "the PDF on my desktop" works without giving a path.

## Approval for other folders

If the model wants to look outside the allowed folders, you're asked once per folder:

```
FileFerret wants to search outside the allowed folders:
  D:\Work
  note: contents it reads there are sent to GeminiClient (gemini-3.5-flash)
Allow for this run? [y/N]
```

- **y** adds that folder for the rest of the question.
- **n** (or Enter) is remembered: the model is told access was denied and not to ask again.
- A whole drive (like `D:\`) gets an extra warning.
- When nobody can answer, for example in a script or with piped input, outside access is always
  denied.

## What leaves your PC

- **Cloud models** (Claude, ChatGPT, Gemini) receive the question and everything the tools return:
  file names, matching lines, and the parts of files the model reads. They don't receive files it
  never looks at.
- **Gemini's free tier** may use that data to improve Google's products.
- **Local models** (Ollama) keep everything on your PC.
- **The PDF cache** stores plain-text copies of PDFs you've searched in
  `%LOCALAPPDATA%\FileFerret\cache`. See [pdfs.md](pdfs.md) to inspect or delete it.

All tools are read-only: FileFerret never changes, moves or deletes your files.
