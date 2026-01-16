from __future__ import annotations

from typing import Iterable, List

from src.models import Paragraph


class ParagraphBuilder:
    def merge_broken_paragraphs(self, blocks: Iterable[dict]) -> List[Paragraph]:
        paragraphs: List[Paragraph] = []
        buffer: list[str] = []
        page: int | None = None

        for block in blocks:
            text = block.get("text", "").strip()
            if not text:
                continue

            if page is None:
                page = block.get("page")

            buffer.append(text)
            if text.endswith(".") or text.endswith("?") or text.endswith("!"):
                paragraphs.append(Paragraph(text=" ".join(buffer), page=page))
                buffer = []
                page = None

        if buffer:
            paragraphs.append(Paragraph(text=" ".join(buffer), page=page))

        return paragraphs

    def detect_paragraph_boundaries(self, lines: Iterable[str]) -> List[int]:
        boundaries: List[int] = []
        for idx, line in enumerate(lines):
            if not line.strip():
                boundaries.append(idx)
        return boundaries
