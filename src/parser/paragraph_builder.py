from __future__ import annotations

from typing import Iterable, List

from src.models import Paragraph


class ParagraphBuilder:
    def build(self, blocks: Iterable[dict]) -> List[Paragraph]:
        """각 블록을 개별 Paragraph로 유지."""
        paragraphs: List[Paragraph] = []
        for block in blocks:
            text = block.get("text") or block.get("content", "")
            if not text or not text.strip():
                continue
            paragraphs.append(
                Paragraph(
                    text=text.strip(),
                    page=block.get("page_idx", 0),
                    bbox=block.get("bbox", [0, 0, 0, 0]),
                )
            )
        return paragraphs

    def merge_broken_paragraphs(self, blocks: Iterable[dict]) -> List[Paragraph]:
        return self.build(blocks)

    def detect_paragraph_boundaries(self, lines: Iterable[str]) -> List[int]:
        boundaries: List[int] = []
        for idx, line in enumerate(lines):
            if not line.strip():
                boundaries.append(idx)
        return boundaries
