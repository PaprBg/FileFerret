"""Errors shared by the extractors (kept separate so cache.py can import them without a cycle)."""


class UnsupportedFileType(Exception):
    """Raised for files no extractor can read yet."""


class ExtractionError(Exception):
    """A supported file that couldn't be read: corrupt, password-protected, ..."""
