import pytest


@pytest.fixture
def docs(tmp_path):
    """A small folder of sample files to search."""
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "wifi.md").write_text(
        "# Home network\n\nRouter: TP-Link\nWiFi password: hunter2\nGuest network: off\n",
        encoding="utf-8",
    )
    (tmp_path / "todo.txt").write_text("buy milk\nrenew car insurance before March\n", encoding="utf-8")
    (tmp_path / "resume.pdf").write_bytes(b"%PDF-1.4 not readable yet")
    (tmp_path / "venv").mkdir()
    (tmp_path / "venv" / "skip.txt").write_text("password in a skipped folder\n", encoding="utf-8")
    return tmp_path.resolve()
