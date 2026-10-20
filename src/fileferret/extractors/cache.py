"""Disk + memory cache of extracted text for file types that are slow to extract (PDF).

Each file's text is stored once per (path, size, modified time) as gzip JSON under
%LOCALAPPDATA%\\FileFerret\\cache (or FILEFERRET_CACHE_DIR). The cache holds plain-text
copies of your files; it's safe to delete at any time (`fileferret cache --clear`).
"""

import gzip
import hashlib
import json
import os
import shutil
from collections.abc import Callable
from pathlib import Path

from fileferret.extractors.errors import ExtractionError

VERSION = 1

Pages = list[list[str]]

# Called with the path whenever a file is actually extracted (not served from cache);
# the CLI uses it to show progress during slow first scans.
on_extract: Callable[[Path], None] | None = None

_memory: dict[tuple[str, int, int], Pages | ExtractionError] = {}


def cache_dir() -> Path:
    if env := os.environ.get("FILEFERRET_CACHE_DIR"):
        return Path(env)
    if local := os.environ.get("LOCALAPPDATA"):
        return Path(local) / "FileFerret" / "cache"
    return Path.home() / ".cache" / "fileferret"


def cached_extract(path: Path, extractor: Callable[[Path], Pages]) -> Pages:
    path = path.resolve()
    stat = path.stat()
    key = (str(path), stat.st_size, stat.st_mtime_ns)

    result = _memory.get(key)
    if result is None:
        result = _load(key)
        if result is None:
            if on_extract:
                on_extract(path)
            try:
                result = extractor(path)
            except ExtractionError as e:
                result = e  # remembered so broken files aren't retried on every run
            _save(key, result)
        _memory[key] = result

    if isinstance(result, ExtractionError):
        raise result
    return result


def stats() -> tuple[int, int]:
    """(number of cached files, total bytes)."""
    files = list(cache_dir().glob("*.json.gz"))
    return len(files), sum(f.stat().st_size for f in files)


def clear() -> None:
    shutil.rmtree(cache_dir(), ignore_errors=True)
    _memory.clear()


def _record_path(path_str: str) -> Path:
    return cache_dir() / (hashlib.sha1(path_str.encode("utf-8")).hexdigest() + ".json.gz")


def _load(key: tuple[str, int, int]) -> Pages | ExtractionError | None:
    path_str, size, mtime_ns = key
    try:
        with gzip.open(_record_path(path_str), "rt", encoding="utf-8") as f:
            record = json.load(f)
    except (OSError, ValueError):
        return None
    if (record.get("version"), record.get("path"), record.get("size"), record.get("mtime_ns")) != (
        VERSION, path_str, size, mtime_ns
    ):
        return None  # file changed since it was cached
    if "error" in record:
        return ExtractionError(record["error"])
    return record.get("pages")


def _save(key: tuple[str, int, int], result: Pages | ExtractionError) -> None:
    path_str, size, mtime_ns = key
    record = {"version": VERSION, "path": path_str, "size": size, "mtime_ns": mtime_ns}
    if isinstance(result, ExtractionError):
        record["error"] = str(result)
    else:
        record["pages"] = result
    target = _record_path(path_str)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(record, f)
        os.replace(tmp, target)
    except OSError:
        pass  # an unwritable cache only costs speed
