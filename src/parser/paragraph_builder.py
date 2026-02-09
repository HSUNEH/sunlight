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

    @staticmethod
    def _should_merge(current_block: dict, next_block: dict, current_text: str, next_text: str) -> bool:
        """두 블록을 병합해야 하는지 판단한다."""
        # title이면 병합하지 않음
        if current_block.get("text_level") == 1 or next_block.get("text_level") == 1:
            return False
        # list면 병합하지 않음
        if current_block.get("type") == "list" or next_block.get("type") == "list":
            return False
        stripped = current_text.rstrip()
        if not stripped:
            return False
        # 컬럼이 바뀌면서 다음 블록이 현재보다 훨씬 위에 있으면 별개 문단
        cur_bbox = current_block.get("bbox", [0, 0, 0, 0])
        nxt_bbox = next_block.get("bbox", [0, 0, 0, 0])
        same_page = current_block.get("page_idx", 0) == next_block.get("page_idx", 0)
        col_change = same_page and abs(cur_bbox[0] - nxt_bbox[0]) > 100
        if col_change and nxt_bbox[1] < cur_bbox[1] - 100:
            return False
        # 다음 블록이 소문자로 시작하면 문단이 이어지는 것 (컬럼/페이지 넘김)
        next_stripped = next_text.lstrip()
        if next_stripped and next_stripped[0].islower():
            return True
        # 현재 텍스트가 문장종결 부호로 끝나면 병합하지 않음
        if stripped[-1] in ".!?:;":
            return False
        return True

    def merge_broken_paragraphs(self, blocks: Iterable[dict]) -> List[Paragraph]:
        """블록을 순회하며 끊어진 문단을 병합한다."""
        block_list = list(blocks)
        if not block_list:
            return []

        paragraphs: List[Paragraph] = []
        i = 0
        while i < len(block_list):
            block = block_list[i]
            text = self._extract_text(block)
            if not text or not text.strip():
                i += 1
                continue

            normalized = self.normalizer.normalize(text.strip())
            merged_text = normalized
            regions = [{"bbox": block.get("bbox", [0, 0, 0, 0]), "page": block.get("page_idx", 0)}]

            # 다음 블록과 병합 가능한지 반복 확인
            while i + 1 < len(block_list):
                next_block = block_list[i + 1]
                next_text = self._extract_text(next_block)
                if not next_text or not next_text.strip():
                    i += 1
                    continue

                next_normalized = self.normalizer.normalize(next_text.strip())
                if self._should_merge(block_list[i], next_block, merged_text, next_normalized):
                    merged_text = merged_text + " " + next_normalized
                    regions.append({"bbox": next_block.get("bbox", [0, 0, 0, 0]), "page": next_block.get("page_idx", 0)})
                    i += 1
                else:
                    break

            paragraphs.append(
                Paragraph(
                    text=merged_text,
                    page=regions[0]["page"],
                    bbox=regions[0]["bbox"],
                    bboxes=regions if len(regions) > 1 else None,
                )
            )
            i += 1

        return paragraphs

    def detect_paragraph_boundaries(self, lines: Iterable[str]) -> List[int]:
        boundaries: List[int] = []
        for idx, line in enumerate(lines):
            if not line.strip():
                boundaries.append(idx)
        return boundaries
