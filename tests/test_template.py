"""Tests for studycraft.template subject-type detection and hints."""

import pytest

from studycraft.template import (
    CHAPTER_TEMPLATE,
    DIFFICULTY_HINTS,
    detect_subject_type,
    difficulty_hint,
    example_format_hint,
)


@pytest.mark.parametrize("subject,expected", [
    ("Introduction to Python Programming", "stem"),
    ("Advanced Java Development", "stem"),
    ("Machine Learning Fundamentals", "stem"),
    ("Web Development with React", "stem"),
    ("Calculus II", "math"),
    ("Linear Algebra", "math"),
    ("Statistics and Probability", "math"),
    ("Physics 101", "math"),
    ("English Grammar", "language"),
    ("Japanese for Beginners", "language"),
    ("TOEFL Preparation", "language"),
    ("History of Art", "humanities"),
    ("Philosophy 101", "humanities"),
    ("Introduction to Sociology", "humanities"),
])
def test_detect_subject_type(subject: str, expected: str):
    assert detect_subject_type(subject) == expected


def test_format_hint_returns_string():
    for stype in ("stem", "math", "language", "humanities"):
        hint = example_format_hint(stype)
        assert isinstance(hint, str)
        assert len(hint) > 10


def test_format_hint_unknown_type():
    hint = example_format_hint("unknown_type")
    assert "appropriate format" in hint


def test_difficulty_hint_all_levels():
    for level in ("beginner", "intermediate", "advanced"):
        hint = difficulty_hint(level)
        assert isinstance(hint, str)
        assert "Target audience" in hint


def test_difficulty_hint_unknown_falls_back():
    hint = difficulty_hint("nonexistent")
    assert hint == DIFFICULTY_HINTS["intermediate"]


def test_difficulty_hints_keys():
    assert set(DIFFICULTY_HINTS.keys()) == {"beginner", "intermediate", "advanced"}


def test_chapter_template_has_required_placeholders():
    for placeholder in ("{chapter_num}", "{chapter_title}", "{subject}", "{subchapters}"):
        assert placeholder in CHAPTER_TEMPLATE, f"Missing placeholder: {placeholder}"


def test_chapter_template_has_all_sections():
    """Template must contain all 8 section headings the validator checks."""
    for section in (
        "Learning Objectives",
        "Core Concepts",
        "Worked Examples",
        "Practice Exercises",
        "Mini Project",
        "Chapter Quiz",
        "Reflection",
        "Tips & Common Mistakes",
    ):
        assert section in CHAPTER_TEMPLATE, f"Template missing section: {section}"
