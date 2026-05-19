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

Detection strategy:
  1. Greedy heading collection — gather ALL potential headings from the document
  2. LLM agent filtering — classify headings as chapters vs subchapters
  3. Fallback heuristics — if no LLM available, use regex-based classification

Post-processing:
  - Appendix, glossary, bibliography, references, and index sections are filtered out.
"""

from __future__ import annotations

import json
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
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"),
    (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
    (5, "V"), (4, "IV"), (1, "I"),
]

_ROMAN_RE = re.compile(r"^(M{0,3})(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$", re.IGNORECASE)


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

# Explicit chapter patterns — require a keyword like "Chapter", "Module", etc.
_CH_PATTERNS_EXPLICIT = [
    re.compile(
        r"^#*\s*(?:chapter|module|unit|section|part|topic)\s+(\d+[\.\d]*)"
        r"[\s:\-\.\u2013\u2014]+(.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^#*\s*(?:chapter|module|unit|section|part|topic)\s+"
        r"((?:M{0,3})(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))"
        r"[\s:\-\.\u2013\u2014]+(.+)$",
        re.IGNORECASE,
    ),
]

# Implicit chapter patterns — bare numbered lines
_CH_PATTERNS_IMPLICIT = [
    re.compile(r"^#*\s*(\d{1,2})\.\s+(.{3,})$"),
    re.compile(r"^#*\s*(\d{1,2})\s+([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)+.*)$"),
]

_CH_PATTERNS = _CH_PATTERNS_EXPLICIT + _CH_PATTERNS_IMPLICIT

# Sub-chapter patterns (numbered: "1.1 Title")
_SUB_PATTERNS = [
    re.compile(r"^#*\s*(\d{1,2}\.\d{1,2})[\.\s:\-\u2013\u2014]+(.{3,})$"),
]

# TOC-style lines (dot leaders before a page number)
_TOC_LINE_RE = re.compile(r"\.\.\.\.+\s*\d+\s*$")

# Trailing page numbers in titles
_TRAILING_PAGE_NUM_RE = re.compile(r"\s{2,}\d{1,5}\s*$")

# ALL-CAPS standalone heading (>= 3 words)
_CAPS_PATTERN = re.compile(r"^([A-Z][A-Z\s\-:]{10,})$")

# Unnumbered subheading: title-case, short, mostly alpha
_UNNUMBERED_HEADING_RE = re.compile(r"^[A-Z][A-Za-z',\-\s&]{2,78}$")

# Skip patterns for appendix/glossary etc.
_SKIP_PATTERN = re.compile(
    r"(?i)^#*\s*(?:appendix|glossary|bibliography|references|index|about\s+the\s+author)",
)

# False-positive heading patterns
_FALSE_HEADING_RE = re.compile(
    r"(?i)^(figure|table|book\s+\d|in this chapter|contents|note|tip|warning|"
    r"press|click|see\s|the\s|a\s|an\s|if\s|for\s|to\s|you\s|this\s|that\s|"
    r"it\s|is\s|are\s|was\s|were\s|has\s|have\s|do\s|does\s|did\s|will\s|"
    r"can\s|could\s|would\s|should\s|may\s|might\s|shall\s|must\s|"
    r"FIGURE|TABLE|BOOK)"
)


# ── Main detector ─────────────────────────────────────────────────────────────


def detect_chapters(text: str, llm_client=None, rag_index=None) -> list[Chapter]:
    lines = [line.rstrip() for line in text.splitlines()]

    # Step 1: Greedy collection of ALL potential headings
    headings = _greedy_collect_headings(lines)

    # Step 2: LLM agent classifies headings into chapters vs subchapters
    if headings and llm_client is not None and len(headings) > 2:
        chapters = _llm_classify_headings(headings, text[:4000], llm_client, lines)
        if chapters and len(chapters) >= 2:
            chapters = [ch for ch in chapters if not _SKIP_PATTERN.match(ch["title"].strip())]
            console.print(
                f"  [green]\u2713 Detected[/green] {len(chapters)} chapter(s) with "
                f"{sum(len(c['subchapters']) for c in chapters)} subchapter(s) [dim](AI-assisted)[/dim]"
            )
            return chapters

    # Step 3: Regex-only classification
    if headings:
        chapters = _regex_classify_headings(headings, lines)
        if chapters and len(chapters) >= 2:
            chapters = [ch for ch in chapters if not _SKIP_PATTERN.match(ch["title"].strip())]
            console.print(
                f"  [green]\u2713 Detected[/green] {len(chapters)} chapter(s) with "
                f"{sum(len(c['subchapters']) for c in chapters)} subchapter(s)"
            )
            return chapters

    # Step 4: Full LLM fallback — let AI read the document and determine structure
    if llm_client is not None:
        console.print("  [yellow]Regex detection insufficient, using AI full-document analysis...[/yellow]")
        chapters = _llm_full_document_analysis(text, llm_client, lines, rag_index)
        if chapters and len(chapters) >= 2:
            chapters = [ch for ch in chapters if not _SKIP_PATTERN.match(ch["title"].strip())]
            console.print(
                f"  [green]\u2713 Detected[/green] {len(chapters)} chapter(s) with "
                f"{sum(len(c['subchapters']) for c in chapters)} subchapter(s) [dim](AI full analysis)[/dim]"
            )
            return chapters

    # Step 5: Ultimate fallback — fixed windows
    result = _fixed_windows(text)
    _attach_text(lines, result)
    chapters = result[0]
    console.print(
        f"  [green]\u2713 Detected[/green] {len(chapters)} chapter(s) with "
        f"{sum(len(c['subchapters']) for c in chapters)} subchapter(s) [dim](fixed windows)[/dim]"
    )
    return chapters


# ── Greedy heading collection ─────────────────────────────────────────────────


@dataclass
class _Heading:
    """A potential heading found in the document."""
    title: str
    start_line: int
    heading_type: str  # "explicit", "numbered_sub", "caps", "unnumbered"
    raw_num: str = ""  # original number if any


@dataclass
class _Span:
    num: str
    title: str
    start_line: int
    end_line: int = -1


def _greedy_collect_headings(lines: list[str]) -> list[_Heading]:
    """Collect ALL potential headings from the document — be greedy."""
    headings: list[_Heading] = []
    seen_titles: set[str] = set()

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Skip TOC lines
        if _TOC_LINE_RE.search(stripped):
            continue

        heading = _try_match_heading(lines, i, stripped)
        if heading is None:
            continue

        # Deduplicate: skip if we've seen this exact title already
        title_key = heading.title.lower().strip()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        headings.append(heading)

    return headings


def _try_match_heading(lines: list[str], i: int, stripped: str) -> _Heading | None:
    """Try to match a line as any type of heading."""
    # 1. Explicit chapter pattern (Chapter N: Title)
    for pat in _CH_PATTERNS_EXPLICIT:
        m = pat.match(stripped)
        if m:
            num_str = m.group(1)
            roman_val = _roman_to_int(num_str)
            if roman_val is not None:
                num_str = str(roman_val)
            title = _clean_title(m.group(2))
            if not title:
                break
            # Skip if "title" looks like a sentence (starts with lowercase word)
            first_word = title.split()[0] if title.split() else ""
            if first_word and first_word[0].islower():
                break
            return _Heading(title=title, start_line=i, heading_type="explicit", raw_num=num_str)

    # 2. Implicit numbered pattern ("1. Title", "1 Title")
    for pat in _CH_PATTERNS_IMPLICIT:
        m = pat.match(stripped)
        if m:
            num_str = m.group(1)
            title = _clean_title(m.group(2))
            if title:
                first_word = title.split()[0] if title.split() else ""
                if first_word and first_word[0].islower():
                    break
                return _Heading(title=title, start_line=i, heading_type="implicit", raw_num=num_str)

    # 3. Numbered sub-pattern (1.1 Title)
    for pat in _SUB_PATTERNS:
        m = pat.match(stripped)
        if m:
            title = _clean_title(m.group(2))
            if title:
                return _Heading(title=title, start_line=i, heading_type="numbered_sub", raw_num=m.group(1))

    # 3. ALL-CAPS heading
    if _CAPS_PATTERN.match(stripped):
        return _Heading(title=stripped.title(), start_line=i, heading_type="caps")

    # 4. Unnumbered heading (title-case short line)
    if _is_potential_heading(lines, i, stripped):
        return _Heading(title=stripped, start_line=i, heading_type="unnumbered")

    return None


def _clean_title(raw: str) -> str:
    """Strip trailing page numbers and whitespace from a title."""
    title = _TRAILING_PAGE_NUM_RE.sub("", raw).strip()
    return title


def _is_potential_heading(lines: list[str], idx: int, stripped: str) -> bool:
    """Heuristic check for unnumbered headings."""
    if not _UNNUMBERED_HEADING_RE.match(stripped):
        return False
    if _FALSE_HEADING_RE.match(stripped):
        return False
    words = stripped.split()
    if len(words) < 3 or len(stripped) > 65:
        return False
    # Must be followed by a longer line (paragraph content)
    if idx + 1 < len(lines):
        next_line = lines[idx + 1].strip()
        if not next_line or len(next_line) < len(stripped):
            return False
    # Previous line should be blank or end a sentence
    if idx > 0:
        prev = lines[idx - 1].strip()
        if prev and prev[-1] not in '.!?:)"\u201d':
            return False
    return True


# ── LLM agent classification ─────────────────────────────────────────────────


def _llm_classify_headings(
    headings: list[_Heading], doc_excerpt: str, llm_client, lines: list[str]
) -> list[Chapter] | None:
    """Use LLM to classify greedy headings into chapters and subchapters."""
    # Build a numbered list of headings for the LLM
    heading_list = "\n".join(
        f"{i+1}. [{h.heading_type}] {h.title}"
        for i, h in enumerate(headings)
    )

    prompt = (
        "You are analyzing a document's structure. Below is a list of potential headings "
        "extracted from the document, along with a short excerpt of the document text.\n\n"
        "Your task: classify each heading as either a TOP-LEVEL CHAPTER or a SUBCHAPTER "
        "(sub-topic within a chapter). Some entries may be FALSE POSITIVES (not real headings) — mark those as SKIP.\n\n"
        "Rules:\n"
        "- A book typically has 3-15 chapters (top-level divisions)\n"
        "- Subchapters are topics WITHIN a chapter\n"
        "- Headings marked [explicit] with 'Chapter N' are almost always top-level chapters\n"
        "- Assign each subchapter to its parent chapter number\n"
        "- If a heading is noise (page header, figure caption, etc.), mark as SKIP\n\n"
        f"DOCUMENT EXCERPT:\n{doc_excerpt[:2000]}\n\n"
        f"HEADINGS:\n{heading_list}\n\n"
        "Return ONLY a JSON array. Each item must have:\n"
        '- "index": the heading number (1-based)\n'
        '- "role": "chapter" or "sub" or "skip"\n'
        '- "parent": chapter index (only for role="sub", null otherwise)\n\n'
        "Example: "
        '[{"index":1,"role":"chapter","parent":null},{"index":2,"role":"sub","parent":1},...]\n'
    )

    try:
        resp = llm_client.chat.completions.create(
            model="openrouter/free",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000,
        )
        content = resp.choices[0].message.content
        if not content:
            return None
        # Strip markdown fences
        content = re.sub(r"^```(?:json)?\n?", "", content.strip())
        content = re.sub(r"\n?```$", "", content)
        data = json.loads(content)
        return _build_chapters_from_classification(data, headings, lines)
    except Exception as exc:
        console.print(f"  [yellow]LLM classification failed: {exc}[/yellow]")
        return None


def _build_chapters_from_classification(
    classification: list[dict], headings: list[_Heading], lines: list[str]
) -> list[Chapter] | None:
    """Build Chapter list from LLM classification results."""
    # Map heading index -> classification
    class_map: dict[int, dict] = {}
    for item in classification:
        idx = item.get("index", 0) - 1  # convert to 0-based
        if 0 <= idx < len(headings):
            class_map[idx] = item

    # Collect chapters in order
    chapter_indices: list[int] = []
    for idx in range(len(headings)):
        info = class_map.get(idx, {})
        if info.get("role") == "chapter":
            chapter_indices.append(idx)

    if len(chapter_indices) < 2:
        return None

    # Build chapters with spans
    chapters: list[Chapter] = []
    for ci, ch_idx in enumerate(chapter_indices):
        h = headings[ch_idx]
        ch_num = h.raw_num or str(ci + 1)

        # Determine text span
        start = h.start_line
        if ci + 1 < len(chapter_indices):
            end = headings[chapter_indices[ci + 1]].start_line - 1
        else:
            end = len(lines) - 1

        text = "\n".join(lines[start : end + 1])

        # Collect subchapters assigned to this chapter
        subs: list[SubChapter] = []
        sub_count = 0
        for idx in range(len(headings)):
            info = class_map.get(idx, {})
            if info.get("role") != "sub":
                continue
            parent = info.get("parent")
            # parent is 1-based index into headings
            parent_idx = (parent - 1) if parent else -1
            if parent_idx == ch_idx:
                sub_count += 1
                sh = headings[idx]
                sub_num = sh.raw_num or f"{ch_num}.{sub_count}"
                # Sub text: from this heading to next heading or chapter end
                sub_start = sh.start_line
                sub_end = _find_next_heading_line(idx, headings, class_map, end)
                subs.append(SubChapter(
                    num=sub_num,
                    title=sh.title,
                    text="\n".join(lines[sub_start : sub_end + 1]),
                ))

        chapters.append(Chapter(num=ch_num, title=h.title, subchapters=subs, text=text))

    return chapters if len(chapters) >= 2 else None


def _find_next_heading_line(
    current_idx: int, headings: list[_Heading], class_map: dict[int, dict], chapter_end: int
) -> int:
    """Find the line where the next heading starts (for sub text boundary)."""
    for idx in range(current_idx + 1, len(headings)):
        info = class_map.get(idx, {})
        if info.get("role") in ("chapter", "sub"):
            return headings[idx].start_line - 1
    return chapter_end


# ── Full LLM document analysis fallback ────────────────────────────────────────


def _llm_full_document_analysis(
    text: str, llm_client, lines: list[str], rag_index=None
) -> list[Chapter] | None:
    """Last-resort AI fallback: send document excerpts and let the LLM determine
    the full chapter/subchapter structure from scratch."""
    # Gather context: beginning, middle, and end of document
    total_len = len(text)
    excerpt_start = text[:3000]
    excerpt_mid = text[total_len // 3 : total_len // 3 + 2000] if total_len > 6000 else ""
    excerpt_end = text[-2000:] if total_len > 5000 else ""

    # If RAG is available, query for structural info
    rag_context = ""
    if rag_index is not None:
        try:
            rag_context = rag_index.query("table of contents chapters sections headings outline")
        except Exception:
            pass

    prompt = (
        "You are analyzing a document to determine its chapter and subchapter structure.\n"
        "The document may use any heading style: numbered, unnumbered, ALL-CAPS, Roman numerals, etc.\n\n"
        "Based on the excerpts below, identify ALL top-level chapters and their subchapters.\n\n"
        f"DOCUMENT START:\n{excerpt_start}\n\n"
    )
    if excerpt_mid:
        prompt += f"DOCUMENT MIDDLE:\n{excerpt_mid}\n\n"
    if excerpt_end:
        prompt += f"DOCUMENT END:\n{excerpt_end}\n\n"
    if rag_context:
        prompt += f"ADDITIONAL CONTEXT (from document index):\n{rag_context[:1500]}\n\n"

    prompt += (
        "Return ONLY a JSON array of chapters. Each chapter has:\n"
        '- "num": chapter number as string\n'
        '- "title": chapter title\n'
        '- "subchapters": array of {"num": "1.1", "title": "Sub Title"}\n\n'
        'Example: [{"num":"1","title":"Introduction","subchapters":[{"num":"1.1","title":"Background"}]}]\n'
    )

    try:
        resp = llm_client.chat.completions.create(
            model="openrouter/free",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=3000,
        )
        content = resp.choices[0].message.content
        if not content:
            return None
        content = re.sub(r"^```(?:json)?\n?", "", content.strip())
        content = re.sub(r"\n?```$", "", content)
        data = json.loads(content)
        return _build_chapters_from_llm_structure(data, lines)
    except Exception as exc:
        console.print(f"  [yellow]Full LLM analysis failed: {exc}[/yellow]")
        return None


def _build_chapters_from_llm_structure(
    data: list[dict], lines: list[str]
) -> list[Chapter] | None:
    """Build Chapter objects from LLM-generated structure by locating titles in text."""
    if not data or len(data) < 2:
        return None

    chapters: list[Chapter] = []
    chapter_starts: list[tuple[int, dict]] = []

    # Locate each chapter's start line in the document
    for ch_data in data:
        title = ch_data.get("title", "").strip()
        num = str(ch_data.get("num", len(chapters) + 1))
        if not title:
            continue
        start_line = _find_title_in_lines(title, lines)
        chapter_starts.append((start_line, ch_data))

    # Sort by start line
    chapter_starts.sort(key=lambda x: x[0])

    for ci, (start, ch_data) in enumerate(chapter_starts):
        end = chapter_starts[ci + 1][0] - 1 if ci + 1 < len(chapter_starts) else len(lines) - 1
        text = "\n".join(lines[start : end + 1])
        num = str(ch_data.get("num", ci + 1))
        title = ch_data.get("title", f"Chapter {num}")

        # Build subchapters
        subs: list[SubChapter] = []
        for sub_data in ch_data.get("subchapters", []):
            sub_title = sub_data.get("title", "").strip()
            sub_num = str(sub_data.get("num", f"{num}.{len(subs) + 1}"))
            if not sub_title:
                continue
            sub_start = _find_title_in_lines(sub_title, lines, search_start=start, search_end=end)
            # Find sub end
            sub_end = end
            for next_sub in ch_data.get("subchapters", [])[len(subs) + 1:]:
                next_title = next_sub.get("title", "")
                if next_title:
                    next_start = _find_title_in_lines(next_title, lines, search_start=sub_start + 1, search_end=end)
                    if next_start > sub_start:
                        sub_end = next_start - 1
                        break
            subs.append(SubChapter(
                num=sub_num,
                title=sub_title,
                text="\n".join(lines[sub_start : sub_end + 1]),
            ))

        chapters.append(Chapter(num=num, title=title, subchapters=subs, text=text))

    return chapters if len(chapters) >= 2 else None


def _find_title_in_lines(
    title: str, lines: list[str], search_start: int = 0, search_end: int | None = None
) -> int:
    """Find the line index where a title appears (fuzzy match)."""
    title_lower = title.lower().strip()
    end = search_end if search_end is not None else len(lines) - 1
    # Exact substring match first
    for i in range(search_start, min(end + 1, len(lines))):
        if title_lower in lines[i].lower():
            return i
    # Fuzzy: match first 20 chars
    short = title_lower[:20]
    for i in range(search_start, min(end + 1, len(lines))):
        if short in lines[i].lower():
            return i
    return search_start


# ── Regex-only fallback classification ────────────────────────────────────────


def _regex_classify_headings(headings: list[_Heading], lines: list[str]) -> list[Chapter]:
    """Fallback: classify headings using only regex patterns (no LLM)."""
    # If we have explicit chapter headings, use those as chapters
    explicit = [h for h in headings if h.heading_type == "explicit"]
    implicit = [h for h in headings if h.heading_type == "implicit"]

    if len(explicit) >= 2:
        # Dedup by raw_num — prefer occurrences NOT in the TOC area (first 40 lines)
        seen: dict[str, _Heading] = {}
        for h in explicit:
            if h.raw_num not in seen:
                seen[h.raw_num] = h
            elif seen[h.raw_num].start_line < 40 and h.start_line >= 40:
                seen[h.raw_num] = h
        chapter_headings = sorted(seen.values(), key=lambda h: h.start_line)
    elif len(implicit) >= 2:
        # Use implicit numbered headings as chapters
        seen_i: dict[str, _Heading] = {}
        for h in implicit:
            if h.raw_num not in seen_i:
                seen_i[h.raw_num] = h
        chapter_headings = sorted(seen_i.values(), key=lambda h: h.start_line)
    else:
        # Use all headings as chapters (old behavior)
        chapter_headings = headings[:20]

    # Sort by document order
    chapter_headings = sorted(chapter_headings, key=lambda h: h.start_line)

    # Build chapters
    chapters: list[Chapter] = []
    for ci, h in enumerate(chapter_headings):
        ch_num = h.raw_num or str(ci + 1)
        start = h.start_line
        end = chapter_headings[ci + 1].start_line - 1 if ci + 1 < len(chapter_headings) else len(lines) - 1
        text = "\n".join(lines[start : end + 1])

        # Find subchapters: only unnumbered, numbered_sub, and caps headings
        # (NOT implicit or explicit — those are chapter-level)
        subs: list[SubChapter] = []
        sub_count = 0
        for sh in headings:
            if sh.heading_type in ("explicit", "implicit"):
                continue
            if sh.start_line <= start or sh.start_line > end:
                continue
            sub_count += 1
            sub_num = sh.raw_num or f"{ch_num}.{sub_count}"
            # Find sub text end
            sub_end = end
            for other in headings:
                if other.start_line > sh.start_line and other.start_line <= end:
                    if other.heading_type not in ("explicit", "implicit"):
                        sub_end = other.start_line - 1
                        break
            subs.append(SubChapter(
                num=sub_num,
                title=sh.title,
                text="\n".join(lines[sh.start_line : sub_end + 1]),
            ))

        chapters.append(Chapter(num=ch_num, title=h.title, subchapters=subs, text=text))

    return chapters


# ── Fixed windows fallback ────────────────────────────────────────────────────


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
        first_line = chunk.strip().splitlines()[0] if chunk.strip() else title
        if len(first_line) < 80:
            title = first_line.strip()
        chapters.append(Chapter(num=str(num), title=title, subchapters=[], text=chunk))
        spans.append(_Span(num=str(num), title=title, start_line=i, end_line=i + window))
        i += window - overlap
        num += 1
    return chapters, spans


# ── Attach text helper ────────────────────────────────────────────────────────


def _attach_text(lines: list[str], result: tuple[list[Chapter], list[_Span]]) -> None:
    chapters, spans = result
    for chapter, span in zip(chapters, spans, strict=True):
        chapter["text"] = "\n".join(lines[span.start_line : span.end_line + 1])


# ── Public helper ─────────────────────────────────────────────────────────────


def chapters_to_outline(chapters: list[Chapter]) -> str:
    """Return a human-readable outline string."""
    lines = []
    for ch in chapters:
        lines.append(f"  {ch['num']}. {ch['title']}")
        for sub in ch["subchapters"]:
            lines.append(f"      {sub['num']} {sub['title']}")
    return "\n".join(lines)
