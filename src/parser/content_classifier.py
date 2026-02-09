from __future__ import annotations


class ContentClassifier:
    def is_body_text(self, block: dict) -> bool:
        if block.get("type") not in {"text", "title", "list"}:
            return False
        if block.get("sub_type") == "ref_text":
            return False
        return True

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
