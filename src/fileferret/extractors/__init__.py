"""Turn files into text with page/line positions.

Every extractor returns a list of pages, each a list of lines, so tools and
citations share the same (path, page, line) addressing across file types.
"""

from pathlib import Path

from fileferret.extractors import cache, pdf_extract, text
from fileferret.extractors.errors import ExtractionError, UnsupportedFileType

Pages = list[list[str]]

# Register ".docx": docx_extract.extract once implemented.
_BY_SUFFIX = {
    ".txt": text.extract,
    ".md": text.extract,
    ".pdf": pdf_extract.extract,
}

# Slow to extract, so their text is cached on disk (see cache.py).
_CACHED = {".pdf"}

# Files bigger than this are skipped when searching. PDFs are mostly images and fonts by size.
_DEFAULT_MAX_BYTES = 5 * 1024 * 1024
_MAX_BYTES = {".pdf": 100 * 1024 * 1024}

SUPPORTED_SUFFIXES = tuple(sorted(_BY_SUFFIX))

__all__ = [
    "ExtractionError", "Pages", "SUPPORTED_SUFFIXES", "UnsupportedFileType",
    "extract", "has_text", "is_supported", "max_bytes",
]


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in _BY_SUFFIX


def max_bytes(path: Path) -> int:
    return _MAX_BYTES.get(path.suffix.lower(), _DEFAULT_MAX_BYTES)


def has_text(pages: Pages) -> bool:
    return any(line.strip() for page in pages for line in page)


def extract(path: Path) -> Pages:
    """Pages of lines. Raises UnsupportedFileType, ExtractionError, or OSError."""
    suffix = path.suffix.lower()
    try:
        extractor = _BY_SUFFIX[suffix]
    except KeyError:
        raise UnsupportedFileType(path.suffix or "(no extension)") from None
    if suffix in _CACHED:
        return cache.cached_extract(path, extractor)
    return extractor(path)
