"""Which folders FileFerret may search, and where the user's common folders are.

Works like Claude Code's working directories: the model may use any path, but anything
outside the allowed roots needs the user's approval, asked once per folder per run.
Relative paths resolve against the first root.
"""

import os
from collections.abc import Callable, Sequence
from pathlib import Path

from fileferret.tools.common import ToolError

# Called with a folder outside the roots; returns True if the user allows searching it.
AskPermission = Callable[[Path], bool]


class Workspace:
    def __init__(self, roots: Sequence[Path], ask_permission: AskPermission | None = None):
        if not roots:
            raise ValueError("at least one root folder is required")
        self.roots = [Path(r).resolve() for r in roots]
        self.ask_permission = ask_permission
        self.denied: list[Path] = []

    @property
    def base(self) -> Path:
        return self.roots[0]

    def resolve(self, path: str = ".", ask: bool = True) -> Path:
        """Turn a model-supplied path into an absolute one, asking the user if it's outside the roots."""
        p = Path(os.path.expandvars(os.path.expanduser(path or ".")))
        if not p.is_absolute():
            p = self.base / p
        p = p.resolve()
        if _inside_any(p, self.roots):
            return p

        folder = p if p.is_dir() else p.parent
        if _inside_any(p, self.denied):
            raise ToolError(f"the user denied access to {folder}; don't ask for it again")
        if not ask or self.ask_permission is None:
            allowed = "; ".join(str(r) for r in self.roots)
            raise ToolError(f"{path} is outside the allowed folders ({allowed})")
        if self.ask_permission(folder):
            self.roots.append(folder)
            return p
        self.denied.append(folder)
        raise ToolError(f"the user denied access to {folder}; don't ask for it again")

    def display(self, path: Path) -> str:
        """Path as shown to the model: relative to base when inside it, else absolute."""
        if _inside(path, self.base):
            return path.relative_to(self.base).as_posix()
        return path.as_posix()


def default_roots(cli_roots: Sequence[Path] | None = None) -> list[Path]:
    """--root values, else FILEFERRET_ROOTS (separated by os.pathsep), else the user folder."""
    if cli_roots:
        return list(cli_roots)
    env = os.environ.get("FILEFERRET_ROOTS", "").strip()
    if env:
        return [Path(os.path.expanduser(p.strip())) for p in env.split(os.pathsep) if p.strip()]
    return [Path.home()]


def known_folders(home: Path | None = None) -> list[tuple[str, Path]]:
    """Desktop/Documents/Downloads that exist, including OneDrive-redirected copies."""
    home = home or Path.home()
    found = []
    for name in ("Desktop", "Documents", "Downloads"):
        for candidate in (home / name, home / "OneDrive" / name):
            if candidate.is_dir():
                found.append((name, candidate))
    return found


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _inside_any(path: Path, roots: Sequence[Path]) -> bool:
    return any(_inside(path, r) for r in roots)
