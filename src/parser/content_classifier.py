from __future__ import annotations


class ContentClassifier:
    def is_body_text(self, block: dict) -> bool:
        return block.get("type") == "paragraph"

    def is_table(self, block: dict) -> bool:
        return block.get("type") == "table"

    def is_figure(self, block: dict) -> bool:
        return block.get("type") == "figure"

    def is_equation(self, block: dict) -> bool:
        return block.get("type") == "equation"

    def is_metadata(self, block: dict) -> bool:
        return block.get("type") == "metadata"

    def is_footnote(self, block: dict) -> bool:
        return block.get("type") == "footnote"

    def is_header_footer(self, block: dict) -> bool:
        return block.get("type") in {"header", "footer"}
