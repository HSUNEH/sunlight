from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Author:
    name: str
    affiliation: Optional[str] = None
    email: Optional[str] = None


@dataclass
class Metadata:
    title: Optional[str] = None
    authors: List[Author] | None = None
    keywords: List[str] | None = None
    doi: Optional[str] = None
    references: List[str] | None = None
