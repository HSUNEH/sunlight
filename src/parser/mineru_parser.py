from __future__ import annotations

from pathlib import Path
from typing import Iterable

from src.models import Figure, Paragraph, ParsedPaper, Table
from src.parser.content_classifier import ContentClassifier
from src.parser.paragraph_builder import ParagraphBuilder


class PaperParser:
    def __init__(self, classifier: ContentClassifier | None = None) -> None:
        self.classifier = classifier or ContentClassifier()
        self.paragraph_builder = ParagraphBuilder()

    def parse(self, pdf_path: str | Path) -> ParsedPaper:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        blocks = self._run_mineru(pdf_path)
        body_blocks = [b for b in blocks if self.classifier.is_body_text(b)]
        paragraphs = self.paragraph_builder.merge_broken_paragraphs(body_blocks)

        tables = [self._to_table(b) for b in blocks if self.classifier.is_table(b)]
        figures = [self._to_figure(b) for b in blocks if self.classifier.is_figure(b)]
        equations = [b["latex"] for b in blocks if self.classifier.is_equation(b)]
        metadata = self._extract_metadata(blocks)

        return ParsedPaper(
            body=paragraphs,
            tables=tables,
            figures=figures,
            equations=equations,
            metadata=metadata,
        )

    def _run_mineru(self, pdf_path: Path) -> Iterable[dict]:
        """Placeholder for MinerU integration.

        Expected output is a list of dict blocks containing fields like:
        {"type": "paragraph"|"table"|"figure"|"equation"|"metadata", ...}
        """
        raise NotImplementedError("MinerU integration not implemented yet")

    def _to_table(self, block: dict) -> Table:
        return Table(
            html=block.get("html", ""),
            caption=block.get("caption"),
            page=block.get("page"),
            table_id=block.get("id"),
        )

    def _to_figure(self, block: dict) -> Figure:
        return Figure(
            path=block.get("path", ""),
            caption=block.get("caption"),
            page=block.get("page"),
            figure_id=block.get("id"),
        )

    def _extract_metadata(self, blocks: Iterable[dict]) -> dict:
        return {
            "raw": [b for b in blocks if self.classifier.is_metadata(b)],
        }
