"""Write tiny real PDFs for tests, without any extra dependency."""

from pathlib import Path


def make_pdf(path: Path, pages: list[list[str]]) -> Path:
    """A PDF with one page per entry; each string becomes one line of text (empty list = no text)."""
    page_ids = [4 + 2 * i for i in range(len(pages))]
    objects = {
        1: "<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Kids [{' '.join(f'{i} 0 R' for i in page_ids)}] /Count {len(pages)} >>",
        3: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for page_id, lines in zip(page_ids, pages):
        ops = ["BT", "/F1 12 Tf", "14 TL", "72 720 Td"] if lines else []
        for line in lines:
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            ops.append(f"({escaped}) Tj T*")
        if lines:
            ops.append("ET")
        stream = "\n".join(ops)
        objects[page_id] = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {page_id + 1} 0 R >>"
        )
        objects[page_id + 1] = f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream"

    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for obj_id in sorted(objects):
        offsets[obj_id] = len(out)
        out += f"{obj_id} 0 obj\n{objects[obj_id]}\nendobj\n".encode("latin-1")
    xref_at = len(out)
    size = max(objects) + 1
    out += f"xref\n0 {size}\n0000000000 65535 f \n".encode()
    for obj_id in range(1, size):
        out += f"{offsets[obj_id]:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))
    return path
