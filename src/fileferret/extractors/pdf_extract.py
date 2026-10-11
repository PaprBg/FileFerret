"""PDF files: one page of lines per PDF page, via pypdf."""

from pathlib import Path


def extract(path: Path) -> list[list[str]]:
    raise NotImplementedError
