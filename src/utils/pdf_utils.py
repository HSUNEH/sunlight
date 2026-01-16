from __future__ import annotations

from pathlib import Path


def ensure_pdf(path: str | Path) -> Path:
    pdf_path = Path(path)
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF: {pdf_path}")
    return pdf_path
