from __future__ import annotations

import json
import subprocess
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

        blocks = list(self._run_mineru(pdf_path))
        body_blocks = [b for b in blocks if self.classifier.is_body_text(b)]

        # References 이후 블록 제거
        ref_idx = None
        for i, b in enumerate(body_blocks):
            text = (b.get("text") or "").strip().upper()
            if b.get("text_level") == 1 and text in ("REFERENCES", "BIBLIOGRAPHY"):
                ref_idx = i
                break
        if ref_idx is not None:
            body_blocks = body_blocks[:ref_idx]

        paragraphs = self.paragraph_builder.build(body_blocks)

        tables = [self._to_table(b) for b in blocks if self.classifier.is_table(b)]
        figures = [self._to_figure(b) for b in blocks if self.classifier.is_figure(b)]
        equations = [b.get("latex", "") for b in blocks if self.classifier.is_equation(b)]
        metadata = self._extract_metadata(blocks)

        return ParsedPaper(
            body=paragraphs,
            tables=tables,
            figures=figures,
            equations=equations,
            metadata=metadata,
        )

    def _run_mineru(self, pdf_path: Path) -> Iterable[dict]:
        """Run MinerU CLI and yield content list blocks."""
        output_root = Path("output")
        content_list_path = (
            output_root
            / pdf_path.stem
            / "hybrid_auto"
            / f"{pdf_path.stem}_content_list.json"
        )
        if not content_list_path.exists():
            output_root.mkdir(parents=True, exist_ok=True)

            devices = ["mps", "cpu"]
            last_error: subprocess.CalledProcessError | None = None
            for device in devices:
                cmd = [
                    "mineru",
                    "-p",
                    str(pdf_path),
                    "-o",
                    str(output_root),
                    "-d",
                    device,
                ]
                try:
                    subprocess.run(cmd, check=True, capture_output=True, text=True)
                    last_error = None
                    break
                except subprocess.CalledProcessError as exc:
                    last_error = exc

            if last_error is not None:
                raise RuntimeError(
                    f"MinerU failed with exit code {last_error.returncode}: "
                    f"{last_error.stderr.strip()}"
                ) from last_error

        if not content_list_path.exists():
            raise FileNotFoundError(f"MinerU output not found: {content_list_path}")

        with content_list_path.open("r", encoding="utf-8") as handle:
            blocks = json.load(handle)

        for block in blocks:
            if isinstance(block, dict):
                yield block

    def _to_table(self, block: dict) -> Table:
        return Table(
            html=block.get("html", ""),
            caption=block.get("caption"),
            page=block.get("page_idx"),
            table_id=block.get("id"),
        )

    def _to_figure(self, block: dict) -> Figure:
        return Figure(
            path=block.get("img_path", ""),
            caption=block.get("caption"),
            page=block.get("page_idx"),
            figure_id=block.get("id"),
        )

    def _extract_metadata(self, blocks: Iterable[dict]) -> dict:
        return {
            "raw": [b for b in blocks if self.classifier.is_metadata(b)],
        }
