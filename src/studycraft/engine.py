"""
StudyCraft – Core engine.

Orchestrates: document loading → chapter detection → RAG indexing
              → web research → LLM generation → export.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from pathlib import Path

from openai import OpenAI
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from .loader import load_document
from .detector import detect_chapters, chapters_to_outline, Chapter
from .rag import RAGIndex
from .researcher import research
from .template import CHAPTER_TEMPLATE
from .validator import validate_chapter

console = Console()

# Type alias for progress callbacks: (current, total, message) -> None
ProgressCallback = Callable[[int, int, str], None] | None

DEFAULT_MODEL = "openrouter/free"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


class StudyCraft:
    """
    Main orchestrator.

    Usage:
        craft = StudyCraft(api_key="sk-...")
        craft.run("path/to/document.pdf")
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        output_dir: str | Path = "output",
        rag_dir: str | Path = "./rag_index",
        rate_limit_seconds: int = 5,
    ) -> None:
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit_seconds = rate_limit_seconds
        self.rag = RAGIndex(persist_dir=rag_dir)

    # ── Public API ────────────────────────────────────────────────────────────

    def run(
        self,
        document_path: str | Path,
        subject: str | None = None,
        resume_from: int = 1,
        only_chapter: int | None = None,
        with_answers: bool = False,
        on_progress: ProgressCallback = None,
    ) -> dict[str, Path]:
        """
        Full pipeline: load → detect → index → generate → export.

        Args:
            document_path: Path to any supported document.
            subject: Override auto-detected subject name.
            resume_from: Skip chapter numbers below this (uses cache).
            only_chapter: Generate only this one chapter (by number).
        """
        doc_path = Path(document_path)

        # 1. Load document
        raw_text = load_document(doc_path)
        if not raw_text.strip():
            raise ValueError("Document appears to be empty or unreadable.")

        # 2. Detect subject name
        doc_subject = subject or _infer_subject(doc_path, raw_text)
        console.print(f"[bold cyan]📚 Subject:[/bold cyan] {doc_subject}")

        # 3. Detect chapters
        console.print("[cyan]🔍 Detecting chapters…[/cyan]")
        chapters = detect_chapters(raw_text)
        if not chapters:
            raise ValueError(
                "Could not detect any chapters. Check the document format."
            )

        console.print(f"\n[bold]Outline:[/bold]\n{chapters_to_outline(chapters)}\n")

        # 4. Index into RAG (clear old index so this doc is isolated)
        self.rag.clear()
        self.rag.index(raw_text, source_name=doc_path.stem)

        # 5. Generate per chapter
        cache_dir = self.output_dir / ".cache"
        cache_dir.mkdir(exist_ok=True)

        generated: list[str] = []

        targets = (
            chapters
            if only_chapter is None
            else [ch for ch in chapters if int(ch["num"].split(".")[0]) == only_chapter]
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Generating chapters…", total=len(targets))

            for idx, ch in enumerate(targets):
                ch_num = ch["num"]
                cache_file = cache_dir / f"ch{ch_num.replace('.', '_')}.md"
                msg = f"Generating chapter {idx + 1} of {len(targets)}: {ch['title'][:40]}"

                if on_progress:
                    on_progress(idx, len(targets), msg)

                if int(ch_num.split(".")[0]) < resume_from and cache_file.exists():
                    progress.print(f"[dim]⏩ Ch {ch_num} — from cache[/dim]")
                    generated.append(cache_file.read_text(encoding="utf-8"))
                    progress.advance(task)
                    continue

                progress.update(task, description=f"Ch {ch_num}: {ch['title'][:40]}…")
                content = self._generate_chapter_with_retry(ch, doc_subject)
                cache_file.write_text(content, encoding="utf-8")
                generated.append(content)
                progress.advance(task)

                if ch is not targets[-1]:
                    time.sleep(self.rate_limit_seconds)

        # 6. Answer key (optional)
        if with_answers:
            if on_progress:
                on_progress(len(targets), len(targets), "Generating answer key…")
            console.print("[cyan]📝 Generating answer key…[/cyan]")
            answer_key = self._generate_answer_key(generated, doc_subject)
            ak_path = self.output_dir / f"{re.sub(r'[^\w\s-]', '', doc_subject).strip().replace(' ', '_')}_Answer_Key.md"
            ak_path.write_text(answer_key, encoding="utf-8")
            console.print(f"[green]✓ Answer Key[/green] → {ak_path}")

        # 7. Export
        combined = "\n\n---\n\n".join(generated)
        safe_name = re.sub(r"[^\w\s-]", "", doc_subject).strip().replace(" ", "_")
        from .export import export_all

        return export_all(
            combined, self.output_dir, base_name=f"{safe_name}_Practice_Guide"
        )

    # ── Chapter generation ────────────────────────────────────────────────────

    def _generate_chapter_with_retry(
        self, chapter: Chapter, subject: str, max_retries: int = 1
    ) -> str:
        """Generate a chapter, auto-retry once on validation failure."""
        content = self._generate_chapter(chapter, subject)
        result = validate_chapter(content, label=f"Ch {chapter['num']}")

        if result.passed or max_retries < 1:
            if not result.passed:
                console.print(
                    f"  [yellow]⚠ Ch {chapter['num']} validation:[/yellow] {result.summary()}"
                )
            return content

        console.print(
            f"  [yellow]⚠ Ch {chapter['num']} failed validation ({result.summary()}) — retrying…[/yellow]"
        )
        time.sleep(self.rate_limit_seconds)
        content = self._generate_chapter(chapter, subject, temperature=0.5)
        retry_result = validate_chapter(content, label=f"Ch {chapter['num']}")
        if not retry_result.passed:
            console.print(
                f"  [yellow]⚠ Ch {chapter['num']} retry still has issues:[/yellow] {retry_result.summary()}"
            )
        return content

    def _generate_chapter(
        self, chapter: Chapter, subject: str, temperature: float = 0.3
    ) -> str:
        sub_titles = [s["title"] for s in chapter["subchapters"]]
        sub_label = (
            "\n".join(f"  - {t}" for t in sub_titles) if sub_titles else "None detected"
        )

        # Context from RAG
        rag_ctx = self.rag.query(f"{chapter['title']} {' '.join(sub_titles)}")

        # Web research
        web_ctx = research(
            subject=subject,
            chapter_title=chapter["title"],
            subchapter_titles=sub_titles,
        )

        # Fill template
        filled_template = (
            CHAPTER_TEMPLATE.replace("{chapter_num}", chapter["num"])
            .replace("{chapter_title}", chapter["title"])
            .replace("{subject}", subject)
            .replace("{subchapters}", sub_label)
        )

        prompt = f"""You are an expert educator and technical writer. \
Generate a complete, high-quality practice guide chapter using EXACTLY the template below.
Fill every placeholder with accurate, practical, subject-specific content.
Do NOT add, remove, or rename any section. Do NOT output anything outside the template.

SUBJECT: {subject}
CHAPTER: {chapter["num"]} — {chapter["title"]}
SUBCHAPTERS: {sub_label}

DOCUMENT CONTEXT (from the uploaded resource):
{chapter["text"][:3000]}

RAG CONTEXT (most relevant document passages):
{rag_ctx}

WEB RESEARCH CONTEXT:
{web_ctx}

TEMPLATE (fill every placeholder — replace all [...] items with real content):
{filled_template}

RULES:
- Use the exact subject "{subject}" throughout — no generic placeholders
- Code/formulas must match the subject (e.g. Python for a Python course, equations for maths)
- All 10 quiz questions must be filled in with real questions
- Keep examples practical and realistic, not toy/trivial examples
- Do not reproduce the placeholder text — replace it entirely
"""

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=4500,
            )
            content = resp.choices[0].message.content.strip()
            # Strip accidental markdown fences
            content = re.sub(r"^```(?:markdown)?\n?", "", content)
            content = re.sub(r"\n```$", "", content)
            return content
        except Exception as exc:
            console.print(f"  [red]✗ LLM error ch {chapter['num']}: {exc}[/red]")
            return (
                f"# Chapter {chapter['num']}: {chapter['title']}\n\n"
                f"<!-- Generation failed: {exc} -->\n"
            )


    # ── Answer key generation ─────────────────────────────────────────────────

    def _generate_answer_key(
        self, chapter_contents: list[str], subject: str
    ) -> str:
        """Generate an answer key from all chapter quiz questions and exercises."""
        # Extract quiz + exercise sections from each chapter
        sections = []
        for content in chapter_contents:
            for heading in ("Chapter Quiz", "Practice Exercises"):
                parts = re.split(rf"(?i)##\s*\d*\.?\s*{heading}", content)
                if len(parts) > 1:
                    section_text = parts[1].split("##")[0].strip()
                    sections.append(f"### {heading}\n{section_text}")

        if not sections:
            return f"# Answer Key — {subject}\n\nNo quiz questions or exercises found."

        prompt = f"""You are an expert educator. Generate a complete answer key for the following quiz questions and practice exercises from a {subject} study guide.

For each question/exercise:
- Restate the question number
- Provide the correct answer with a brief explanation

QUESTIONS AND EXERCISES:
{chr(10).join(sections[:6000])}

Format as clean Markdown with clear numbering."""

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=4500,
            )
            body = resp.choices[0].message.content.strip()
            return f"# 🔑 Answer Key — {subject}\n\n{body}"
        except Exception as exc:
            return f"# Answer Key — {subject}\n\n<!-- Generation failed: {exc} -->"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _infer_subject(doc_path: Path, text: str) -> str:
    """
    Guess the subject from the filename or first non-empty line of text.
    Falls back to the filename stem.
    """
    # Try first meaningful line
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and len(stripped) < 100:
            return stripped
    # Fall back to filename
    return doc_path.stem.replace("_", " ").replace("-", " ").title()
