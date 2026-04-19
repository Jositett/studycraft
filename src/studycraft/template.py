"""
StudyCraft – Universal practice guide template.

Placeholders:
  {chapter_num}     — "3" or "3.1"
  {chapter_title}   — full chapter title
  {subject}         — overall subject / course name
  {subchapters}     — bulleted list of subchapter titles (or "None detected")
  {example_format}  — subject-specific format hint (code, equations, prose, etc.)
"""

from __future__ import annotations

import re

# ── Subject type detection ────────────────────────────────────────────────────

_STEM_KEYWORDS = re.compile(
    r"(?i)\b(python|java|javascript|typescript|c\+\+|rust|go|ruby|php|swift|kotlin|"
    r"programming|software|algorithm|data.?struct|machine.?learn|deep.?learn|"
    r"web.?dev|devops|docker|kubernetes|sql|database|api|html|css|react|node)"
)
_MATH_KEYWORDS = re.compile(
    r"(?i)\b(math|calculus|algebra|geometry|statistics|probability|linear|"
    r"differential|integral|trigonometry|discrete|number.?theory|physics|chemistry)"
)
_LANGUAGE_KEYWORDS = re.compile(
    r"(?i)\b(english|spanish|french|german|japanese|chinese|korean|arabic|"
    r"grammar|vocabulary|linguistics|language.?learn|esl|toefl|ielts)"
)


def detect_subject_type(subject: str) -> str:
    """Classify subject into stem, math, language, or humanities."""
    if _STEM_KEYWORDS.search(subject):
        return "stem"
    if _MATH_KEYWORDS.search(subject):
        return "math"
    if _LANGUAGE_KEYWORDS.search(subject):
        return "language"
    return "humanities"


def example_format_hint(subject_type: str) -> str:
    """Return a format hint for worked examples based on subject type."""
    return {
        "stem": "Use code blocks with the appropriate programming language. Show input/output.",
        "math": "Use LaTeX-style equations and step-by-step algebraic manipulation.",
        "language": "Use vocabulary tables, sentence examples, and translation exercises.",
        "humanities": "Use prose analysis, source excerpts, and argumentative examples.",
    }.get(subject_type, "Use the most appropriate format for the subject.")


CHAPTER_TEMPLATE = """\
# 📖 Practice Guide — {subject}
## Chapter {chapter_num}: {chapter_title}

**Subchapters covered:** {subchapters}

---

## 1. Learning Objectives
By the end of this chapter, you will be able to:
- [Actionable objective 1 — specific and measurable]
- [Actionable objective 2]
- [Actionable objective 3]
- [Actionable objective 4]
- [Actionable objective 5]

> *Why this matters: [One sentence connecting this chapter to real-world application.]*

---

## 2. Core Concepts & Theory

### 2.1 Key Definitions
| Term | Definition |
|------|-----------|
| [Term 1] | [Clear, concise definition] |
| [Term 2] | [Clear, concise definition] |
| [Term 3] | [Clear, concise definition] |

### 2.2 How It Works
[2–3 paragraphs explaining the underlying concepts. Use analogies where helpful.
Cover each subchapter in turn. Be concrete, not abstract.]

### 2.3 Common Patterns & Rules
- **[Pattern/Rule 1]**: [Explanation]
- **[Pattern/Rule 2]**: [Explanation]
- **[Pattern/Rule 3]**: [Explanation]

> *Insight: [A mental model or mindset shift that makes this chapter "click".]*

---

## 3. Worked Examples
*Study each example carefully before attempting the exercises.*

### Example 1 — [Descriptive title reflecting a realistic scenario]
**Problem:** [State the problem clearly]

**Solution:**
```
[Code, formula, diagram, worked solution — use the appropriate format for {subject}]
```

**Explanation:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

> *Tip: [A practical insight about this example.]*

---

### Example 2 — [Descriptive title]
**Problem:** [State the problem]

**Solution:**
```
[Solution]
```

**Explanation:**
1. [Step 1]
2. [Step 2]

> *Tip: [Insight.]*

---

### Example 3 — [Descriptive title]
**Problem:** [State the problem]

**Solution:**
```
[Solution]
```

**Explanation:**
1. [Step 1]
2. [Step 2]

> *Tip: [Insight.]*

---

## 4. Practice Exercises
*Attempt each exercise independently before checking answers or hints.*

### 🟢 Basic (Recall & Apply)
1. [Exercise testing direct recall of a definition or simple application]
2. [Exercise testing a straightforward procedure]
3. [Exercise requiring single-step reasoning]

### 🟡 Intermediate (Analyse & Connect)
1. [Exercise requiring multi-step reasoning or combining two concepts]
2. [Exercise involving a realistic scenario with some complexity]
3. [Exercise that asks the learner to compare or contrast two ideas]

### 🔴 Challenge (Evaluate & Create)
1. [Open-ended problem that requires synthesis across the whole chapter]
2. [Scenario-based problem that mirrors a real professional challenge]

---

## 5. Mini Project
**Build / Solve:** [A self-contained, realistic project that exercises ALL concepts from this chapter]

**Context:** [Why this project matters in practice]

**Requirements:**
- [Requirement 1]
- [Requirement 2]
- [Requirement 3]

**Extension:** [A stretch goal for advanced learners]

---

## 6. Chapter Quiz
*Answer from memory — no notes, no tools.*

1. [Factual recall question]
2. [Factual recall question]
3. [Conceptual understanding question]
4. [Conceptual understanding question]
5. [Application question — "Given X, what would happen if…"]
6. [Application question]
7. [Analysis question — "Why does… / What is the difference between…"]
8. [Analysis question]
9. [Synthesis question — "How would you design…"]
10. [Evaluation question — "Which approach is better and why…"]

---

## 7. Reflection
*Think about these after completing the exercises:*
- What was the most surprising or counterintuitive idea in this chapter?
- Which concept took the longest to understand? What helped it click?
- Where could you apply what you learned today in a real project or task?
- What question do you still have after studying this chapter?
- How does this chapter connect to what you already knew before?

---

## 8. Tips & Common Mistakes

### Watch Out For
- **[Mistake 1]**: [Why learners make it and how to avoid it]
- **[Mistake 2]**: [Why learners make it and how to avoid it]
- **[Mistake 3]**: [Why learners make it and how to avoid it]

### Best Practices
- [Best practice 1]
- [Best practice 2]
- [Best practice 3]

### Further Reading
- [Resource 1 — book, article, or documentation]
- [Resource 2]

---

✅ **Chapter Complete — Next Step:**
[A specific, actionable prompt that encourages the learner to consolidate and move forward.]
"""
