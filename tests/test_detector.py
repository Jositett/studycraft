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


# ── Running page headers (should not create duplicate chapters) ────────────────

_RUNNING_HEADER_DOC = """\
CHAPTER 1  Getting Started      1
Welcome to the course. This chapter covers basics.
CHAPTER 1  Getting Started      3
More content on the same topic.
CHAPTER 1  Getting Started      5
Even more content.

CHAPTER 2  Advanced Topics      7
Now we move to advanced material.
CHAPTER 2  Advanced Topics      9
Continuing advanced topics.
"""


def test_running_headers_deduped():
    chapters = detect_chapters(_RUNNING_HEADER_DOC)
    assert len(chapters) == 2
    assert chapters[0]["title"] == "Getting Started"
    assert chapters[1]["title"] == "Advanced Topics"


# ── TOC with dot leaders should not create chapters ───────────────────────────

_TOC_DOC = """\
Table of Contents
Chapter 1: Introduction ........................ 1
Chapter 2: Variables ........................... 15
Chapter 3: Functions ........................... 30

Chapter 1: Introduction
This is the actual introduction content.

Chapter 2: Variables
Variables store data in memory.

Chapter 3: Functions
Functions encapsulate reusable logic.
"""


def test_toc_lines_filtered():
    chapters = detect_chapters(_TOC_DOC)
    assert len(chapters) == 3
    # Should use the actual chapter headings, not TOC entries
    assert "actual introduction" in chapters[0]["text"]


# ── Unnumbered subheadings ────────────────────────────────────────────────────

_UNNUMBERED_SUB_DOC = """\
Chapter 1: Excel Basics
This chapter covers the basics of Excel.

Creating a New Workbook
To create a workbook, go to File > New.

Entering Data in Cells
Click a cell and start typing.

Chapter 2: Formatting
This chapter covers formatting.

Changing Font Styles
Select cells and use the Home tab.
"""


def test_unnumbered_subheadings():
    chapters = detect_chapters(_UNNUMBERED_SUB_DOC)
    assert len(chapters) == 2
    # Should detect unnumbered subheadings
    sub_titles = [s["title"] for s in chapters[0]["subchapters"]]
    assert "Creating a New Workbook" in sub_titles
    assert "Entering Data in Cells" in sub_titles


# ── Module/Unit/Part keywords ─────────────────────────────────────────────────

_MODULE_DOC = """\
Module 1: Introduction to Python
Python is a versatile language.

Module 2: Data Structures
Lists, dicts, and sets.

Module 3: Object-Oriented Programming
Classes and inheritance.
"""

_UNIT_DOC = """\
Unit 1: Foundations
Basic concepts.

Unit 2: Intermediate Skills
Building on foundations.

Unit 3: Advanced Topics
Expert-level material.
"""

_PART_DOC = """\
Part 1: Getting Started
Setup and installation.

Part 2: Core Concepts
The main ideas.

Part 3: Applications
Real-world usage.
"""


@pytest.mark.parametrize("doc", [_MODULE_DOC, _UNIT_DOC, _PART_DOC])
def test_alternative_keywords(doc: str):
    chapters = detect_chapters(doc)
    assert len(chapters) == 3


# ── Mixed heading styles (explicit chapters with numbered subs) ───────────────

_MIXED_DOC = """\
Chapter 1: Introduction
1.1 Background
Some background info.
1.2 Objectives
Course objectives.

Chapter 2: Methods
2.1 Qualitative Methods
Description of qualitative.
2.2 Quantitative Methods
Description of quantitative.
2.3 Mixed Methods
Combining both.
"""


def test_mixed_explicit_and_numbered_subs():
    chapters = detect_chapters(_MIXED_DOC)
    assert len(chapters) == 2
    assert len(chapters[0]["subchapters"]) == 2
    assert len(chapters[1]["subchapters"]) == 3
    assert chapters[0]["subchapters"][0]["title"] == "Background"
    assert chapters[1]["subchapters"][2]["title"] == "Mixed Methods"


# ── Sentence starting with "Chapter N" should not be a chapter ────────────────

_SENTENCE_CHAPTER_DOC = """\
Chapter 1: Introduction
This is the introduction.
Chapter 3 of this book explains advanced topics in detail.
More intro content here.

Chapter 2: Variables
Variables store data.
As mentioned in Chapter 1, variables are fundamental.
"""


def test_sentence_with_chapter_not_detected():
    chapters = detect_chapters(_SENTENCE_CHAPTER_DOC)
    assert len(chapters) == 2
    assert chapters[0]["title"] == "Introduction"
    assert chapters[1]["title"] == "Variables"


# ── Very short document ───────────────────────────────────────────────────────

def test_very_short_document():
    chapters = detect_chapters("Hello world")
    assert len(chapters) >= 1  # should at least return something


# ── Empty document ────────────────────────────────────────────────────────────

def test_empty_document():
    chapters = detect_chapters("")
    assert chapters == [] or len(chapters) >= 0  # should not crash
