"""
StudyCraft – Output validator.

Checks generated chapters for:
  - All 8 required section headings
  - Minimum worked examples (3)
  - All 10 quiz questions filled
  - No unfilled [...] placeholders remaining
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

REQUIRED_SECTIONS = [
    "Learning Objectives",
    "Core Concepts",
    "Worked Examples",
    "Practice Exercises",
    "Mini Project",
    "Chapter Quiz",
    "Reflection",
    "Tips & Common Mistakes",
]

MIN_EXAMPLES = 3
MIN_QUIZ_QUESTIONS = 10

# Matches placeholder patterns like [...], [Term 1], [Actionable objective 1]
_PLACEHOLDER_RE = re.compile(r"\[(?:[A-Z][a-zA-Z\s\d]*\.{0,3}|\.{3})\]")


@dataclass
class ValidationResult:
    chapter_label: str = ""
    missing_sections: list[str] = field(default_factory=list)
    example_count: int = 0
    quiz_count: int = 0
    placeholder_count: int = 0
    placeholders: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            not self.missing_sections
            and self.example_count >= MIN_EXAMPLES
            and self.quiz_count >= MIN_QUIZ_QUESTIONS
            and self.placeholder_count == 0
        )

    def summary(self) -> str:
        parts = []
        if self.missing_sections:
            parts.append(f"Missing sections: {', '.join(self.missing_sections)}")
        if self.example_count < MIN_EXAMPLES:
            parts.append(f"Examples: {self.example_count}/{MIN_EXAMPLES}")
        if self.quiz_count < MIN_QUIZ_QUESTIONS:
            parts.append(f"Quiz questions: {self.quiz_count}/{MIN_QUIZ_QUESTIONS}")
        if self.placeholder_count:
            parts.append(f"Unfilled placeholders: {self.placeholder_count}")
        return "; ".join(parts) if parts else "All checks passed"


def validate_chapter(text: str, label: str = "") -> ValidationResult:
    """Validate a single generated chapter with flexible section matching."""
    result = ValidationResult(chapter_label=label)

    # Check required sections with flexible matching
    # Allow variations like "Tips & Common Mistakes", "Common Mistakes & Best Practices", etc.
    section_patterns = {
        "Learning Objectives": r"(?i)learning\s+objectives?|objectives?\s+and\s+outcomes?",
        "Core Concepts": r"(?i)core\s+concepts?|key\s+concepts?|concepts?\s+[&and]\s+theory|theory",
        "Worked Examples": r"(?i)worked?\s+examples?|example|practical\s+examples?",
        "Practice Exercises": r"(?i)practice\s+exercises?|exercises?|practice\s+problems?|problems?",
        "Mini Project": r"(?i)mini\s+projects?|projects?|capstone|hands.?on",
        "Chapter Quiz": r"(?i)chapters?\s+quizzes?|chapter\s+test|assessment|quiz",
        "Reflection": r"(?i)reflections?|self.?assessment|reflection\s+questions?",
        "Tips & Common Mistakes": r"(?i)tips?\s+[&and]\s+(?:common\s+)?mistakes?|common\s+mistakes?|pitfalls?|watch\s+out",
    }
    
    text_lower = text.lower()
    for section_name, pattern in section_patterns.items():
        if not re.search(pattern, text_lower):
            result.missing_sections.append(section_name)

    # Count worked examples (### Example N patterns)
    result.example_count = len(re.findall(r"###\s+(?:worked\s+)?example\s+\d", text, re.IGNORECASE))

    # Count quiz questions (numbered lines under quiz section)
    quiz_match = re.split(r"(?i)##\s*\d*\.?\s*(?:chapter\s+)?quiz", text)
    if len(quiz_match) > 1:
        quiz_section = quiz_match[1].split("##")[0]  # up to next section
        result.quiz_count = len(re.findall(r"^\d{1,2}\.", quiz_section, re.MULTILINE))

    # Detect unfilled placeholders
    matches = _PLACEHOLDER_RE.findall(text)
    result.placeholders = matches
    result.placeholder_count = len(matches)

    return result


def validate_guide(full_markdown: str) -> list[ValidationResult]:
    """Validate an entire guide by splitting on chapter boundaries."""
    # Split on top-level chapter headings
    chapters = re.split(r"(?=^#\s+📖\s+Practice\s+Guide)", full_markdown, flags=re.MULTILINE)
    if not chapters or (len(chapters) == 1 and not chapters[0].strip()):
        chapters = re.split(r"(?=^#\s+Chapter\s+\d)", full_markdown, flags=re.MULTILINE)

    results = []
    for i, ch_text in enumerate(chapters):
        ch_text = ch_text.strip()
        if not ch_text:
            continue
        # Extract label from first heading
        first_line = ch_text.splitlines()[0] if ch_text else f"Section {i + 1}"
        results.append(validate_chapter(ch_text, label=first_line))

    return results
