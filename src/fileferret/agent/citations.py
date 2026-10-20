"""Pull [path:L12] citations out of the model's answer and check them against the real files."""

import re

from fileferret.agent.answer import Citation
from fileferret.extractors import ExtractionError, UnsupportedFileType, extract
from fileferret.tools.common import ToolError
from fileferret.workspace import Workspace

# [path:L12], [path:L12-L15], [path:L12-15], [path:p3:L12]
CITATION_RE = re.compile(r"\[([^\[\]]+?):(?:p(\d+):)?L(\d+)(?:-L?(\d+))?\]")

MAX_QUOTE_CHARS = 500


def extract_citations(text: str, ws: Workspace) -> list[Citation]:
    citations: list[Citation] = []
    seen = set()
    for m in CITATION_RE.finditer(text):
        path, page, start, end = m.group(1).strip(), m.group(2), int(m.group(3)), m.group(4)
        key = (path, page, start, end)
        if key in seen:
            continue
        seen.add(key)
        citation = Citation(path, start, int(end) if end else start, int(page) if page else None)
        verify(citation, ws)
        citations.append(citation)
    return citations


def verify(citation: Citation, ws: Workspace) -> None:
    """Fill in the quote and mark verified if the cited lines really exist."""
    try:
        # Never prompt here: a citation outside the allowed folders simply can't be verified.
        pages = extract(ws.resolve(citation.path, ask=False))
    except (ToolError, UnsupportedFileType, ExtractionError, OSError):
        return
    page = citation.page or 1
    if not 1 <= page <= len(pages):
        return
    lines = pages[page - 1]
    if not 1 <= citation.line_start <= citation.line_end <= len(lines):
        return
    quote = "\n".join(lines[citation.line_start - 1 : citation.line_end]).strip()
    citation.quote = quote[:MAX_QUOTE_CHARS]
    citation.verified = True
