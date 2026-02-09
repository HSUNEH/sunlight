from __future__ import annotations

import re

_ACKNOWLEDGMENT_PATTERN = re.compile(
    r"^(this work|this research|this study|this paper|this project|the authors?)"
    r".*\b(support|fund|grant|sponsor|acknowledg\w*|fellowship|scholarship)",
    re.IGNORECASE | re.DOTALL,
)


class ContentClassifier:
    def is_body_text(self, block: dict) -> bool:
        if block.get("type") not in {"text", "title", "list"}:
            return False
        if block.get("sub_type") == "ref_text":
            return False
        if self.is_acknowledgment(block):
            return False
        return True

    @staticmethod
    def is_acknowledgment(block: dict) -> bool:
        """사사 표기(funding/acknowledgment 각주)를 감지."""
        text = (block.get("text") or "").strip()
        if _ACKNOWLEDGMENT_PATTERN.search(text):
            return True
        return False

    def is_table(self, block: dict) -> bool:
        return block.get("type") == "table"

    def is_figure(self, block: dict) -> bool:
        return block.get("type") == "image"

    def is_equation(self, block: dict) -> bool:
        return block.get("type") == "equation"

    def is_metadata(self, block: dict) -> bool:
        return block.get("type") in {
            "header",
            "footer",
            "page_number",
            "aside_text",
            "page_footnote",
            "code",
        }

    def is_footnote(self, block: dict) -> bool:
        return block.get("type") == "page_footnote"

    def is_header_footer(self, block: dict) -> bool:
        return block.get("type") in {"header", "footer"}
