"""Turn files into text with page/line positions.

Every extractor returns a list of pages, each a list of lines, so tools and
citations share the same (path, page, line) addressing across file types.
"""

from pathlib import Path

from fileferret.extractors import text

Pages = list[list[str]]

# Register ".pdf": pdf_extract.extract and ".docx": docx_extract.extract once implemented.
_BY_SUFFIX = {
    ".txt": text.extract,
    ".md": text.extract,
}

SUPPORTED_SUFFIXES = tuple(sorted(_BY_SUFFIX))


class UnsupportedFileType(Exception):
    """Raised for files no extractor can read yet."""


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in _BY_SUFFIX


def extract(path: Path) -> Pages:
    try:
        extractor = _BY_SUFFIX[path.suffix.lower()]
    except KeyError:
        raise UnsupportedFileType(path.suffix or "(no extension)") from None
    return extractor(path)
