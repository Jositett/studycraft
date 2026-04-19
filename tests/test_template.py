"""Tests for studycraft.template subject-type detection."""

import pytest

from studycraft.template import detect_subject_type, example_format_hint


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
