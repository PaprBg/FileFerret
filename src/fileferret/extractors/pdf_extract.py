"""PDF files: one page of lines per PDF page, via pypdf.

Only the PDF's text layer is read. Scanned pages (images) come back as empty pages.
"""

import logging
from pathlib import Path

from pypdf import PdfReader

from fileferret.extractors.errors import ExtractionError

# pypdf logs a warning for every slightly malformed PDF; those aren't useful to the user.
logging.getLogger("pypdf").setLevel(logging.ERROR)


def extract(path: Path) -> list[list[str]]:
    try:
        reader = PdfReader(path)
        if reader.is_encrypted and not reader.decrypt(""):
            raise ExtractionError("password-protected PDF")
        return [(page.extract_text() or "").splitlines() for page in reader.pages]
    except ExtractionError:
        raise
    except Exception as e:  # pypdf raises many exception types for damaged files
        raise ExtractionError(f"can't read PDF: {e}") from None
