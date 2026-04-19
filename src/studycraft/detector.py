"""
StudyCraft – Chapter & subchapter detector.

Analyses raw document text and returns a structured outline:
    [
        {
            "num": "1",
            "title": "Introduction to Streams",
            "subchapters": [
                {"num": "1.1", "title": "What Is a Stream?"},
                {"num": "1.2", "title": "Lazy Evaluation"},
            ],
            "text": "<full text of this chapter>",
        },
        ...
    ]

Detection strategy (in order of preference):
  1. Explicit numbered headings  — "Chapter 1", "CHAPTER 1", "1.", "1 Title"
  2. Roman numeral headings      — "Chapter I", "Chapter IV", etc.
  3. ALL-CAPS section headers    — standalone lines of ≥3 uppercase words
  4. Fixed-size windows          — fallback when no structure is found

Post-processing:
  - Appendix, glossary, bibliography, references, and index sections are filtered out.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypedDict

from rich.console import Console

console = Console()


# ── Types ─────────────────────────────────────────────────────────────────────


class SubChapter(TypedDict):
    num: str
    title: str
    text: str


class Chapter(TypedDict):
    num: str
    title: str
    subchapters: list[SubChapter]
    text: str


# ── Roman numeral helper ─────────────────────────────────────────────────────

_ROMAN_MAP = [
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
]

_ROMAN_RE = re.compile(
    r"^(M{0,3})(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$", re.IGNORECASE
)


def _roman_to_int(s: str) -> int | None:
    s = s.upper().strip()
    if not s or not _ROMAN_RE.match(s):
        return None
    result = 0
    i = 0
    for value, numeral in _ROMAN_MAP:
        while s[i : i + len(numeral)] == numeral:
            result += value
            i += len(numeral)
    return result if result > 0 else None


# ── Patterns ──────────────────────────────────────────────────────────────────

# Top-level chapter patterns (order matters — more specific first)
_CH_PATTERNS = [
    # "Chapter 1: Title" / "CHAPTER 1 - Title" / "Chapter 1. Title"
    re.compile(
        r"^#*\s*(?:chapter|module|unit|section|part|topic)\s+(\d+[\.\d]*)"
        r"[\s:\-\.\u2013\u2014]+(.+)$",
        re.IGNORECASE,
    ),
    # "Chapter I: Title" / "Chapter IV - Title" (Roman numerals)
    re.compile(
        r"^#*\s*(?:chapter|module|unit|section|part|topic)\s+"
        r"((?:M{0,3})(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))"
        r"[\s:\-\.\u2013\u2014]+(.+)$",
        re.IGNORECASE,
    ),
    # "1. Title" or "1 Title" (at line start, title >= 3 chars)
    re.compile(r"^#*\s*(\d{1,2})\.\s+(.{3,})$"),
    # "1 Some Title Here" — number then >=2 capitalised words
    re.compile(r"^#*\s*(\d{1,2})\s+([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)+.*)$"),
]

# Sub-chapter patterns
_SUB_PATTERNS = [
    # "1.1 Title" / "1.1. Title" / "1.1: Title"
    re.compile(r"^#*\s*(\d{1,2}\.\d{1,2})[\.\s:\-\u2013\u2014]+(.{3,})$"),
]

# ALL-CAPS standalone heading (>= 3 words, no lowercase)
_CAPS_PATTERN = re.compile(r"^([A-Z][A-Z\s\-:]{10,})$")

# Appendix / glossary / bibliography patterns to skip
_SKIP_PATTERN = re.compile(
    r"(?i)^#*\s*(?:appendix|glossary|bibliography|references|index|about\s+the\s+author)",
)


# ── Main detector ─────────────────────────────────────────────────────────────


def detect_chapters(text: str) -> list[Chapter]:
    lines = [line.rstrip() for line in text.splitlines()]

    result = _detect_numbered(lines)
    if not result or len(result[0]) < 2:
        result = _detect_caps(lines)
    if not result or len(result[0]) < 2:
        result = _fixed_windows(text)

    _attach_text(lines, result)
    chapters = result[0]
    _detect_subchapters(chapters)

    # Filter out appendix/glossary/bibliography sections
    chapters = [ch for ch in chapters if not _SKIP_PATTERN.match(ch["title"].strip())]

    console.print(
        f"  [green]\u2713 Detected[/green] {len(chapters)} chapter(s) with "
        f"{sum(len(c['subchapters']) for c in chapters)} subchapter(s)"
    )
    return chapters


# ── Detection strategies ──────────────────────────────────────────────────────


@dataclass
class _Span:
    num: str
    title: str
    start_line: int
    end_line: int = -1


def _detect_numbered(lines: list[str]) -> tuple[list[Chapter], list[_Span]]:
    spans: list[_Span] = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        for pat in _CH_PATTERNS:
            m = pat.match(stripped)
            if m:
                num_str = m.group(1)
                # Convert Roman numerals to Arabic for consistent numbering
                roman_val = _roman_to_int(num_str)
                if roman_val is not None:
                    num_str = str(roman_val)
                spans.append(_Span(num=num_str, title=m.group(2).strip(), start_line=i))
                break

    if len(spans) < 2:
        return [], []

    # assign end lines
    for i, span in enumerate(spans):
        span.end_line = (
            spans[i + 1].start_line - 1 if i + 1 < len(spans) else len(lines) - 1
        )

    return [
        Chapter(num=s.num, title=s.title, subchapters=[], text="") for s in spans
    ], spans


def _detect_caps(lines: list[str]) -> tuple[list[Chapter], list[_Span]]:
    spans: list[_Span] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if _CAPS_PATTERN.match(stripped):
            spans.append(
                _Span(num=str(len(spans) + 1), title=stripped.title(), start_line=i)
            )

    if len(spans) < 2:
        return [], []

    for i, span in enumerate(spans):
        span.end_line = (
            spans[i + 1].start_line - 1 if i + 1 < len(spans) else len(lines) - 1
        )

    return [
        Chapter(num=s.num, title=s.title, subchapters=[], text="") for s in spans
    ], spans


def _fixed_windows(
    text: str, window: int = 3000, overlap: int = 200
) -> tuple[list[Chapter], list[_Span]]:
    """Fallback: split text into fixed-size overlapping windows as 'chapters'."""
    chapters: list[Chapter] = []
    spans: list[_Span] = []
    words = text.split()
    i = 0
    num = 1
    while i < len(words):
        chunk = " ".join(words[i : i + window])
        title = f"Section {num}"
        # Try to extract a meaningful title from first non-empty line
        first_line = chunk.strip().splitlines()[0] if chunk.strip() else title
        if len(first_line) < 80:
            title = first_line.strip()
        chapters.append(Chapter(num=str(num), title=title, subchapters=[], text=chunk))
        spans.append(
            _Span(num=str(num), title=title, start_line=i, end_line=i + window)
        )
        i += window - overlap
        num += 1
    return chapters, spans


# ── Attach full text to chapters ──────────────────────────────────────────────


def _attach_text(lines: list[str], result: tuple[list[Chapter], list[_Span]]) -> None:
    chapters, spans = result
    for chapter, span in zip(chapters, spans):
        chapter["text"] = "\n".join(lines[span.start_line : span.end_line + 1])


def _detect_subchapters(chapters: list[Chapter]) -> None:
    """Scan each chapter's text for subchapter headings."""
    for ch in chapters:
        subs: list[SubChapter] = []
        sub_spans: list[_Span] = []
        lines = ch["text"].splitlines()

        for i, line in enumerate(lines):
            stripped = line.strip()
            for pat in _SUB_PATTERNS:
                m = pat.match(stripped)
                if m:
                    sub_spans.append(
                        _Span(num=m.group(1), title=m.group(2).strip(), start_line=i)
                    )
                    break

        for j, span in enumerate(sub_spans):
            end = (
                sub_spans[j + 1].start_line - 1
                if j + 1 < len(sub_spans)
                else len(lines) - 1
            )
            subs.append(
                SubChapter(
                    num=span.num,
                    title=span.title,
                    text="\n".join(lines[span.start_line : end + 1]),
                )
            )

        ch["subchapters"] = subs


# ── Public helper ─────────────────────────────────────────────────────────────


def chapters_to_outline(chapters: list[Chapter]) -> str:
    """Return a human-readable outline string."""
    lines = []
    for ch in chapters:
        lines.append(f"  {ch['num']}. {ch['title']}")
        for sub in ch["subchapters"]:
            lines.append(f"      {sub['num']} {sub['title']}")
    return "\n".join(lines)
