from __future__ import annotations

from typing import Iterable, List

from src.models import Paragraph
from src.parser.latex_normalizer import LatexNormalizer


class ParagraphBuilder:
    def __init__(self, normalizer: LatexNormalizer | None = None):
        self.normalizer = normalizer or LatexNormalizer()

    @staticmethod
    def _extract_text(block: dict) -> str:
        """블록에서 텍스트를 추출한다.

        우선순위: text -> content -> list_items (join)
        """
        text = block.get("text") or block.get("content") or ""
        if not text:
            items = block.get("list_items")
            if isinstance(items, list) and items:
                text = "\n".join(str(item) for item in items)
        return text

    def build(self, blocks: Iterable[dict]) -> List[Paragraph]:
        """각 블록을 개별 Paragraph로 유지."""
        paragraphs: List[Paragraph] = []
        for block in blocks:
            text = self._extract_text(block)
            if not text or not text.strip():
                continue
            # LaTeX 수식 정규화 적용
            normalized_text = self.normalizer.normalize(text.strip())
            paragraphs.append(
                Paragraph(
                    text=normalized_text,
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
