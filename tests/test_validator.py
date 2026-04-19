"""Tests for studycraft.validator."""

from studycraft.validator import (
    validate_chapter,
    validate_guide,
    REQUIRED_SECTIONS,
    MIN_EXAMPLES,
    MIN_QUIZ_QUESTIONS,
)


_GOOD_CHAPTER = """\
# 📖 Practice Guide — Python
## Chapter 1: Variables

## 1. Learning Objectives
- Understand variables

## 2. Core Concepts & Theory
Concepts here.

## 3. Worked Examples

### Example 1 — Assigning a variable
**Problem:** Assign x = 5
**Solution:** x = 5

### Example 2 — String variable
**Problem:** Create a name
**Solution:** name = "Alice"

### Example 3 — Multiple assignment
**Problem:** Assign a, b, c
**Solution:** a, b, c = 1, 2, 3

## 4. Practice Exercises
Do these exercises.

## 5. Mini Project
Build a calculator.

## 6. Chapter Quiz
1. What is a variable?
2. How do you assign a value?
3. What types exist?
4. What is an integer?
5. Given x=5, what is x+1?
6. How do you swap variables?
7. Why use descriptive names?
8. What is the difference between int and float?
9. How would you design a config system?
10. Which naming convention is better and why?

## 7. Reflection
Think about what you learned.

## 8. Tips & Common Mistakes
Avoid common errors.
"""

_BAD_CHAPTER = """\
# Chapter 1: Variables

## 1. Learning Objectives
- [Actionable objective 1]

## 2. Core Concepts & Theory
[Term 1] is important.

## 3. Worked Examples

### Example 1 — Basic
**Problem:** [State the problem]
"""


def test_good_chapter_passes():
    result = validate_chapter(_GOOD_CHAPTER, label="Ch 1")
    assert result.passed is True
    assert result.missing_sections == []
    assert result.example_count == MIN_EXAMPLES
    assert result.quiz_count == MIN_QUIZ_QUESTIONS
    assert result.placeholder_count == 0
    assert result.summary() == "All checks passed"


def test_bad_chapter_missing_sections():
    result = validate_chapter(_BAD_CHAPTER, label="Ch 1")
    assert not result.passed
    # Must be missing these specific sections
    for section in ("Practice Exercises", "Mini Project", "Chapter Quiz", "Reflection", "Tips & Common Mistakes"):
        assert section in result.missing_sections, f"Should report {section} as missing"


def test_bad_chapter_has_placeholders():
    result = validate_chapter(_BAD_CHAPTER, label="Ch 1")
    assert result.placeholder_count > 0
    # Verify actual placeholder text is captured
    assert any("[Actionable objective 1]" == p for p in result.placeholders)
    assert any("[Term 1]" == p for p in result.placeholders)


def test_bad_chapter_low_examples():
    result = validate_chapter(_BAD_CHAPTER)
    assert result.example_count == 1
    assert result.example_count < MIN_EXAMPLES


def test_bad_chapter_zero_quiz():
    result = validate_chapter(_BAD_CHAPTER)
    assert result.quiz_count == 0


def test_example_count_exact():
    result = validate_chapter(_GOOD_CHAPTER)
    assert result.example_count == 3


def test_quiz_count_exact():
    result = validate_chapter(_GOOD_CHAPTER)
    assert result.quiz_count == 10


def test_summary_lists_all_failures():
    result = validate_chapter(_BAD_CHAPTER)
    summary = result.summary()
    assert "Missing sections" in summary
    assert "Examples:" in summary
    assert "Quiz questions:" in summary
    assert "Unfilled placeholders:" in summary


def test_validate_guide_splits_and_validates():
    ch2 = _GOOD_CHAPTER.replace("Chapter 1", "Chapter 2").replace("Practice Guide — Python", "Practice Guide — Java")
    two_chapters = _GOOD_CHAPTER + "\n\n---\n\n" + ch2
    results = validate_guide(two_chapters)
    assert len(results) == 2
    assert all(r.passed for r in results)
    assert results[0].chapter_label != results[1].chapter_label


def test_validate_guide_empty():
    results = validate_guide("")
    assert results == []


def test_label_preserved():
    result = validate_chapter(_GOOD_CHAPTER, label="My Chapter")
    assert result.chapter_label == "My Chapter"


def test_required_sections_count():
    """Ensure REQUIRED_SECTIONS matches the 8 sections in the template."""
    assert len(REQUIRED_SECTIONS) == 8
