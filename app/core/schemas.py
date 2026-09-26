"""Structured data returned by the extraction pipeline (Stage 1).

These are plain dataclasses on purpose: `app.core` must stay free of Flask and
database imports so it can be unit tested and run from a script.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Line:
    """A single cleaned line of text with the metadata later stages need.

    `index` is the position of the line in the whole document (0-based) and
    `page_line_index` its position within its page. Stage 2 uses these to point
    at the exact place a section heading or a skill was found.
    """

    text: str
    original_text: str
    page: int
    index: int
    page_line_index: int

    @property
    def is_blank(self) -> bool:
        return not self.text.strip()

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "original_text": self.original_text,
            "page": self.page,
            "index": self.index,
            "page_line_index": self.page_line_index,
        }


@dataclass
class Page:
    number: int
    text: str
    char_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "text": self.text,
            "char_count": self.char_count,
        }


@dataclass
class ExtractionResult:
    """Everything Stage 2 needs, and nothing it does not."""

    text: str
    lines: list[Line]
    pages: list[Page]
    method: str
    page_count: int
    char_count: int
    word_count: int
    is_probably_scanned: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def line_count(self) -> int:
        return len(self.lines)

    def lines_on_page(self, page: int) -> list[Line]:
        return [line for line in self.lines if line.page == page]

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "lines": [line.to_dict() for line in self.lines],
            "pages": [page.to_dict() for page in self.pages],
            "method": self.method,
            "page_count": self.page_count,
            "char_count": self.char_count,
            "word_count": self.word_count,
            "is_probably_scanned": self.is_probably_scanned,
            "warnings": list(self.warnings),
        }
