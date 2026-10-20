import pytest

from fileferret.extractors import cache
from fileferret.workspace import Workspace
from pdf_util import make_pdf


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path_factory, monkeypatch):
    """Every test gets its own empty PDF cache; the real one is never touched."""
    monkeypatch.setenv("FILEFERRET_CACHE_DIR", str(tmp_path_factory.mktemp("cache")))
    cache._memory.clear()
    yield
    cache._memory.clear()


@pytest.fixture
def docs(tmp_path):
    """A Workspace over a small folder of sample files (no approval callback: outside = denied)."""
    root = tmp_path / "root"
    (root / "notes").mkdir(parents=True)
    (root / "notes" / "wifi.md").write_text(
        "# Home network\n\nRouter: TP-Link\nWiFi password: hunter2\nGuest network: off\n",
        encoding="utf-8",
    )
    (root / "todo.txt").write_text("buy milk\nrenew car insurance before March\n", encoding="utf-8")
    (root / "resume.pdf").write_bytes(b"%PDF-1.4 corrupt")  # a broken PDF
    (root / "photo.jpg").write_bytes(b"\xff\xd8\xff not a readable type")
    (root / "docs").mkdir()
    make_pdf(root / "docs" / "report.pdf", [
        ["Annual Report 2026", "Prepared by Finance"],
        ["Quarterly revenue grew 12%", "Costs fell slightly"],
    ])
    make_pdf(root / "docs" / "scan.pdf", [[]])  # a page with no text layer, like a scan
    (root / "venv").mkdir()
    (root / "venv" / "skip.txt").write_text("password in a skipped folder\n", encoding="utf-8")
    (root / "AppData").mkdir()
    (root / "AppData" / "cache.txt").write_text("password in AppData\n", encoding="utf-8")
    # Real failure case: a story naming Marguerite that never uses the word "story",
    # plus a decoy word list that also contains the name.
    (root / "Downloads").mkdir()
    (root / "Downloads" / "The_Lighthouse_Keepers_Last_Lantern.txt").write_text(
        "THE LIGHTHOUSE KEEPER'S LAST LANTERN\n\n"
        "On the far edge of a windswept cape stood a lighthouse. Its keeper was Marguerite.\n\n"
        "Marguerite polished the old lantern every Sunday.\n\n"
        "One November night the power failed, and Marguerite lit the lantern.\n",
        encoding="utf-8",
    )
    (root / "Desktop").mkdir()
    (root / "Desktop" / "lexicon.txt").write_text("Margot NNP\nMarguerite NNP\n", encoding="utf-8")
    return Workspace([root])


@pytest.fixture
def outside(tmp_path):
    """A folder next to the workspace root, i.e. outside the allowed folders."""
    folder = tmp_path / "outside"
    folder.mkdir()
    (folder / "secret.md").write_text("line one\nthe secret is 42\n", encoding="utf-8")
    return folder.resolve()
