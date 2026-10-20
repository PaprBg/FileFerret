from pathlib import Path

import pytest

from fileferret.tools import ToolError
from fileferret.workspace import Workspace, default_roots, known_folders


class Approver:
    """Fake permission prompt that records which folders it was asked about."""

    def __init__(self, answer):
        self.answer = answer
        self.asked = []

    def __call__(self, folder):
        self.asked.append(folder)
        return self.answer


def test_relative_paths_resolve_under_base_and_round_trip(docs):
    p = docs.resolve("notes/wifi.md")
    assert p == docs.base / "notes" / "wifi.md"
    assert docs.display(p) == "notes/wifi.md"
    assert docs.resolve(docs.display(p)) == p


def test_outside_without_callback_is_refused(docs, outside):
    with pytest.raises(ToolError, match="outside the allowed folders"):
        docs.resolve(str(outside / "secret.md"))


def test_approved_folder_is_added_and_not_asked_again(docs, outside):
    approve = Approver(True)
    ws = Workspace(docs.roots, approve)
    p = ws.resolve(str(outside / "secret.md"))
    assert p == outside / "secret.md"
    assert approve.asked == [outside]
    assert outside in ws.roots
    ws.resolve(str(outside))
    assert len(approve.asked) == 1
    # outside paths are shown absolute so they round-trip
    assert ws.resolve(ws.display(p)) == p


def test_denied_folder_is_remembered(docs, outside):
    deny = Approver(False)
    ws = Workspace(docs.roots, deny)
    with pytest.raises(ToolError, match="denied"):
        ws.resolve(str(outside / "secret.md"))
    with pytest.raises(ToolError, match="denied"):
        ws.resolve(str(outside))
    assert len(deny.asked) == 1


def test_ask_false_never_prompts(docs, outside):
    approve = Approver(True)
    ws = Workspace(docs.roots, approve)
    with pytest.raises(ToolError):
        ws.resolve(str(outside / "secret.md"), ask=False)
    assert approve.asked == []


def test_default_roots_precedence(monkeypatch, tmp_path):
    monkeypatch.setenv("FILEFERRET_ROOTS", f"{tmp_path / 'a'}{__import__('os').pathsep}{tmp_path / 'b'}")
    assert default_roots([Path("x")]) == [Path("x")]
    assert default_roots(None) == [tmp_path / "a", tmp_path / "b"]
    monkeypatch.setenv("FILEFERRET_ROOTS", "")
    assert default_roots(None) == [Path.home()]


def test_known_folders_finds_desktop_and_onedrive(tmp_path):
    (tmp_path / "Desktop").mkdir()
    (tmp_path / "OneDrive" / "Documents").mkdir(parents=True)
    assert known_folders(tmp_path) == [
        ("Desktop", tmp_path / "Desktop"),
        ("Documents", tmp_path / "OneDrive" / "Documents"),
    ]
