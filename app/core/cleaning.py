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

# How many lines at the top and bottom of a page can hold a header/footer, and
# how many words a repeated line needs before it is treated as one.
EDGE_LINES = 2
MIN_RUNNING_LINE_WORDS = 3

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


def _position_keys(line_count: int, position: int) -> list[str]:
    """Name the page-edge slots a line sits in, e.g. "top:0" or "bottom:1"."""
    keys = []
    if position < EDGE_LINES:
        keys.append(f"top:{position}")
    from_bottom = line_count - 1 - position
    if from_bottom < EDGE_LINES:
        keys.append(f"bottom:{from_bottom}")
    return keys


def looks_like_running_line(text: str) -> bool:
    """Is this text plausible as a running header/footer rather than content?

    A single word such as "Python" is deliberately not plausible: a skill can
    legitimately end two pages, and losing it would destroy evidence that later
    stages need. Headers and footers in practice carry a name, a contact
    detail, a document title or a page marker.
    """
    stripped = text.strip()
    if not stripped or len(stripped) > 80:
        return False
    if _PAGE_NUMBER_RE.match(stripped):
        return True
    lowered = stripped.lower()
    if any(marker in lowered for marker in ("@", "http", "page ", "resume", "curriculum vitae")):
        return True
    return len(stripped.split()) >= MIN_RUNNING_LINE_WORDS


def find_running_lines(page_texts: list[str], min_pages: int = 2) -> set[tuple[str, str]]:
    """Find running headers/footers as (position key, text) pairs.

    A line is only treated as an artifact when it repeats in the *same* slot at
    the top or bottom of at least `min_pages` pages and reads like a header or
    footer. Matching it by text alone would delete legitimate repeated content
    from the body of the document.
    """
    if len(page_texts) < min_pages:
        return set()

    counter: Counter[tuple[str, str]] = Counter()
    for page_text in page_texts:
        lines = [clean_line(line) for line in page_text.splitlines()]
        lines = [line for line in lines if line]
        for position, line in enumerate(lines):
            if not looks_like_running_line(line):
                continue
            for key in _position_keys(len(lines), position):
                counter[(key, line)] += 1

    return {pair for pair, count in counter.items() if count >= min_pages}


def is_noise_line(text: str, position_keys: list[str], running: set[tuple[str, str]]) -> bool:
    """Noise is a bare page number, or a running line in its own page slot."""
    stripped = text.strip()
    if not stripped:
        return False
    if _PAGE_NUMBER_RE.match(stripped):
        return True
    return any((key, stripped) in running for key in position_keys)


def build_lines(pages: list[Page], drop_repeated: bool = True) -> list[Line]:
    """Turn page texts into cleaned `Line` objects with page/line metadata.

    Line-wrapped hyphenated words ("Java-\\nScript") are joined back onto the
    line where the word starts.
    """
    running = find_running_lines([page.text for page in pages]) if drop_repeated else set()

    lines: list[Line] = []
    for page in pages:
        raw_lines = page.text.splitlines()
        non_blank = [clean_line(raw) for raw in raw_lines]
        non_blank = [line for line in non_blank if line]
        seen_non_blank = 0
        pending_hyphen = False

        for page_line_index, raw in enumerate(raw_lines):
            cleaned = clean_line(raw)
            position_keys: list[str] = []
            if cleaned:
                position_keys = _position_keys(len(non_blank), seen_non_blank)
                seen_non_blank += 1

            if is_noise_line(cleaned, position_keys, running):
                # A dropped line breaks the adjacency a hyphen wrap relies on.
                pending_hyphen = False
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

            if not cleaned:
                # A blank line ends the wrap too: the hyphen was real.
                pending_hyphen = False
                if lines and lines[-1].is_blank:
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
