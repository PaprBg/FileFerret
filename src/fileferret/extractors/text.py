"""Plain text files (.txt, .md): a single page of lines."""

from pathlib import Path


def extract(path: Path) -> list[list[str]]:
    # utf-8-sig drops a BOM if present; undecodable bytes become U+FFFD instead of failing.
    return [path.read_text(encoding="utf-8-sig", errors="replace").splitlines()]
