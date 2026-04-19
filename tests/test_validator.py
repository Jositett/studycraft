"""Tests for studycraft.validator."""

from studycraft.validator import validate_chapter, validate_guide


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
    assert result.passed
    assert result.summary() == "All checks passed"


def test_bad_chapter_fails():
    result = validate_chapter(_BAD_CHAPTER, label="Ch 1")
    assert not result.passed
    assert result.missing_sections  # missing several sections
    assert result.placeholder_count > 0


def test_example_count():
    result = validate_chapter(_GOOD_CHAPTER)
    assert result.example_count == 3


def test_quiz_count():
    result = validate_chapter(_GOOD_CHAPTER)
    assert result.quiz_count == 10


def test_bad_chapter_low_examples():
    result = validate_chapter(_BAD_CHAPTER)
    assert result.example_count < 3


def test_validate_guide_splits_chapters():
    two_chapters = _GOOD_CHAPTER + "\n\n---\n\n" + _GOOD_CHAPTER.replace("Chapter 1", "Chapter 2")
    results = validate_guide(two_chapters)
    assert len(results) == 2
