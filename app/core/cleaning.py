"""Basic text cleaning for extracted PDF text (Stage 1).

The goal is to make the text predictable for later stages without losing the
line structure: one input line stays one output line, so page and line numbers
remain meaningful. Only blank-line runs are collapsed, and that happens after
the per-line cleaning.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

from app.core.schemas import Line, Page

BULLET_CHARS = "\u2022\u25cf\u25aa\u25e6\u2023\u2043\u00b7\u2219\u25cb\u25a0\u00a7"

_QUOTE_MAP = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
    "\u00a0": " ",
    "\u200b": "",
    "\ufeff": "",
}

# pdfplumber emits "(cid:NNN)" when a glyph has no unicode mapping, which is
# very common for bullet characters in resumes.
_CID_RE = re.compile(r"\(cid:\d+\)")
_BULLET_RE = re.compile(rf"^\s*[{re.escape(BULLET_CHARS)}]\s*")
_DASH_BULLET_RE = re.compile(r"^\s*[-*\u2043]\s+")
_MULTISPACE_RE = re.compile(r"[ \t]+")
_HYPHEN_WRAP_RE = re.compile(r"(\w)-$")
_PAGE_NUMBER_RE = re.compile(r"^(?:page\s*)?\d+(?:\s*(?:/|of)\s*\d+)?$", re.IGNORECASE)


def normalize_unicode(text: str) -> str:
    """Fold ligatures and exotic punctuation down to plain ASCII-ish text."""
    text = unicodedata.normalize("NFKC", text)
    for source, target in _QUOTE_MAP.items():
        text = text.replace(source, target)
    return text


def clean_line(text: str) -> str:
    """Clean one line: normalize unicode, unify bullets, squeeze whitespace."""
    cleaned = normalize_unicode(text)
    cleaned = cleaned.replace("\t", " ")
    if _CID_RE.match(cleaned.lstrip()):
        cleaned = "- " + _CID_RE.sub(" ", cleaned).lstrip()
    else:
        cleaned = _CID_RE.sub(" ", cleaned)
    if _BULLET_RE.match(cleaned):
        cleaned = _BULLET_RE.sub("- ", cleaned)
    elif _DASH_BULLET_RE.match(cleaned):
        cleaned = _DASH_BULLET_RE.sub("- ", cleaned)
    cleaned = _MULTISPACE_RE.sub(" ", cleaned)
    return cleaned.strip()


def find_repeated_lines(page_texts: list[str], min_pages: int = 2) -> set[str]:
    """Find running headers/footers: short lines repeated on several pages.

    Only the first and last two lines of each page are considered, so a skill
    listed on every page is never mistaken for a footer.
    """
    if len(page_texts) < min_pages:
        return set()

    counter: Counter[str] = Counter()
    for page_text in page_texts:
        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        candidates = lines[:2] + lines[-2:]
        for candidate in set(candidates):
            if len(candidate) <= 80:
                counter[candidate] += 1

    return {line for line, count in counter.items() if count >= min_pages}


def is_noise_line(text: str, repeated: set[str]) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped in repeated:
        return True
    return bool(_PAGE_NUMBER_RE.match(stripped))


def build_lines(pages: list[Page], drop_repeated: bool = True) -> list[Line]:
    """Turn page texts into cleaned `Line` objects with page/line metadata.

    Line-wrapped hyphenated words ("Java-\\nScript") are joined back onto the
    line where the word starts.
    """
    repeated = find_repeated_lines([page.text for page in pages]) if drop_repeated else set()

    lines: list[Line] = []
    for page in pages:
        page_line_index = 0
        pending_hyphen = False
        for raw in page.text.splitlines():
            cleaned = clean_line(raw)
            if is_noise_line(cleaned, repeated):
                continue

            if pending_hyphen and cleaned:
                previous = lines[-1]
                joined = previous.text[:-1] + cleaned
                lines[-1] = Line(
                    text=joined,
                    original_text=previous.original_text + " " + raw.strip(),
                    page=previous.page,
                    index=previous.index,
                    page_line_index=previous.page_line_index,
                )
                pending_hyphen = bool(_HYPHEN_WRAP_RE.search(joined))
                continue

            if not cleaned and lines and lines[-1].is_blank:
                continue

            lines.append(
                Line(
                    text=cleaned,
                    original_text=raw,
                    page=page.number,
                    index=len(lines),
                    page_line_index=page_line_index,
                )
            )
            page_line_index += 1
            pending_hyphen = bool(_HYPHEN_WRAP_RE.search(cleaned))

    while lines and lines[-1].is_blank:
        lines.pop()
    while lines and lines[0].is_blank:
        lines.pop(0)

    return [
        Line(
            text=line.text,
            original_text=line.original_text,
            page=line.page,
            index=position,
            page_line_index=line.page_line_index,
        )
        for position, line in enumerate(lines)
    ]


def lines_to_text(lines: list[Line]) -> str:
    return "\n".join(line.text for line in lines)
