# PDFs

## What is read

FileFerret reads a PDF's **text layer**, page by page, using `pypdf`. Citations include the page:

```
report.pdf:p3:L12      page 3, line 12
report.pdf:p3:L12-L15  page 3, lines 12 to 15
```

Line numbers follow the order of the extracted text. With columns or tables they may not match
the visual lines on the page.

## What can't be read yet

- **Scanned pages and drawings.** Pages that are images have no text layer. FileFerret reports
  them as "no text layer (probably a scanned image)" instead of guessing. Engineering drawing
  sets often fall into this group: their text layer may hold only the title block.
- **Password-protected PDFs** are reported as such and skipped.
- **PDFs over 100 MB** are skipped when searching.

## The text cache

Extracting text takes about 25 ms per page, so searching a folder of hundreds of PDFs would take
minutes every time. FileFerret extracts each PDF once and caches the text:

- Location: `%LOCALAPPDATA%\FileFerret\cache` (or `FILEFERRET_CACHE_DIR` if set).
- A PDF is re-read automatically when it changes (its size or modified time differs).
- PDFs that can't be read are remembered too, so they aren't retried on every run.
- The first search of a big PDF folder is slow; `-v` prints `(reading x.pdf for the first time)`
  for each new PDF. Measured on a Desktop with 35 PDFs: 8.6 s the first time, 0.7 s after.

The cache holds plain-text copies of the PDFs you've searched. To inspect or delete it:

```powershell
fileferret cache          # location, number of files, size
fileferret cache --clear  # delete it
```

`.txt` and `.md` files are read directly and never copied into the cache.
