"""Tests for studycraft.detector."""

import pytest

from studycraft.detector import chapters_to_outline, detect_chapters

# ── Numbered heading detection ────────────────────────────────────────────────

_NUMBERED_DOC = """\
Chapter 1: Introduction
This is the intro content.

Chapter 2: Variables
Variables store data.

Chapter 3: Functions
Functions encapsulate logic.
"""

_DOTTED_DOC = """\
1. Introduction
This is the intro.

2. Variables and Types
Variables store data.

3. Control Flow
If/else and loops.
"""


@pytest.mark.parametrize("doc,expected_count", [
    (_NUMBERED_DOC, 3),
    (_DOTTED_DOC, 3),
])
def test_numbered_detection(doc: str, expected_count: int):
    chapters = detect_chapters(doc)
    assert len(chapters) == expected_count


def test_numbered_titles():
    chapters = detect_chapters(_NUMBERED_DOC)
    assert chapters[0]["title"] == "Introduction"
    assert chapters[1]["title"] == "Variables"
    assert chapters[2]["title"] == "Functions"


def test_chapter_text_populated():
    chapters = detect_chapters(_NUMBERED_DOC)
    assert "intro content" in chapters[0]["text"]
    assert "store data" in chapters[1]["text"]


# ── ALL-CAPS detection ────────────────────────────────────────────────────────

_CAPS_DOC = """\
INTRODUCTION TO THE COURSE
Welcome to this course.

VARIABLES AND DATA TYPES
Variables store values.

CONTROL FLOW STATEMENTS
If, else, loops.
"""


def test_caps_detection():
    chapters = detect_chapters(_CAPS_DOC)
    assert len(chapters) == 3
    assert chapters[0]["title"] == "Introduction To The Course"


# ── Fixed-window fallback ─────────────────────────────────────────────────────

def test_fixed_window_fallback():
    plain = "word " * 10000  # no headings at all
    chapters = detect_chapters(plain)
    assert len(chapters) >= 2  # should split into windows


# ── Subchapter detection ─────────────────────────────────────────────────────

_SUB_DOC = """\
Chapter 1: Introduction
1.1 What Is Python
Python is a language.
1.2 Installing Python
Download from python.org.

Chapter 2: Basics
2.1 Variables
Store data.
"""


def test_subchapter_detection():
    chapters = detect_chapters(_SUB_DOC)
    assert len(chapters) == 2
    assert len(chapters[0]["subchapters"]) == 2
    assert chapters[0]["subchapters"][0]["title"] == "What Is Python"
    assert len(chapters[1]["subchapters"]) == 1


# ── Outline helper ────────────────────────────────────────────────────────────

def test_chapters_to_outline():
    chapters = detect_chapters(_SUB_DOC)
    outline = chapters_to_outline(chapters)
    assert "1. Introduction" in outline
    assert "1.1 What Is Python" in outline
    assert "2. Basics" in outline


# ── Roman numeral detection ───────────────────────────────────────────────────

_ROMAN_DOC = """\
Chapter I: Introduction
This is the intro.

Chapter II: Variables
Variables store data.

Chapter III: Functions
Functions encapsulate logic.
"""


def test_roman_numeral_detection():
    chapters = detect_chapters(_ROMAN_DOC)
    assert len(chapters) == 3
    assert chapters[0]["num"] == "1"
    assert chapters[1]["num"] == "2"
    assert chapters[2]["num"] == "3"
    assert chapters[0]["title"] == "Introduction"


# ── Appendix / glossary filtering ─────────────────────────────────────────────

_APPENDIX_DOC = """\
Chapter 1: Introduction
Intro content.

Chapter 2: Core Topics
Core content.

Appendix A: Extra Tables
Some tables.

Glossary
Term definitions.

Bibliography
References here.
"""


def test_appendix_glossary_filtered():
    chapters = detect_chapters(_APPENDIX_DOC)
    titles = [ch["title"] for ch in chapters]
    assert "Introduction" in titles
    assert "Core Topics" in titles
    for t in titles:
        assert "Appendix" not in t
        assert "Glossary" not in t
        assert "Bibliography" not in t
