from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Paragraph:
    text: str
    page: Optional[int] = None
    block_id: Optional[str] = None
    bbox: Optional[List[float]] = None


@dataclass
class Table:
    html: str
    caption: Optional[str] = None
    page: Optional[int] = None
    table_id: Optional[str] = None


@dataclass
class Figure:
    path: str
    caption: Optional[str] = None
    page: Optional[int] = None
    figure_id: Optional[str] = None


@dataclass
class ParsedPaper:
    body: List[Paragraph]
    tables: List[Table]
    figures: List[Figure]
    equations: List[str]
    metadata: dict
