"""
StudyCraft – Core engine.

Orchestrates: document loading -> chapter detection -> RAG indexing
              -> web research -> LLM generation -> export.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
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
from .template import CHAPTER_TEMPLATE, detect_subject_type, example_format_hint
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

    # -- Public API ------------------------------------------------------------

    def run(
        self,
        document_path: str | Path,
        subject: str | None = None,
        resume_from: int = 1,
        only_chapter: int | None = None,
        with_answers: bool = False,
        on_progress: ProgressCallback = None,
        context_files: list[str | Path] | None = None,
        workers: int = 1,
        theme: str | None = None,
    ) -> dict[str, Path]:
        """
        Full pipeline: load -> detect -> index -> generate -> export.

        Args:
            document_path: Path to any supported document.
            subject: Override auto-detected subject name.
            resume_from: Skip chapter numbers below this (uses cache).
            only_chapter: Generate only this one chapter (by number).
            context_files: Extra documents to index into RAG (not generated).
            workers: Number of parallel workers for chapter generation.
        """
        doc_path = Path(document_path)

        # 1. Load document
        raw_text = load_document(doc_path)
        if not raw_text.strip():
            raise ValueError("Document appears to be empty or unreadable.")

        # 2. Detect subject name
        doc_subject = subject or _infer_subject(doc_path, raw_text)
        console.print(f"[bold cyan]Subject:[/bold cyan] {doc_subject}")

        # 3. Detect chapters
        console.print("[cyan]Detecting chapters...[/cyan]")
        chapters = detect_chapters(raw_text)
        if not chapters:
            raise ValueError(
                "Could not detect any chapters. Check the document format."
            )

        console.print(f"\n[bold]Outline:[/bold]\n{chapters_to_outline(chapters)}\n")

        # 4. Index into RAG (clear old index so this doc is isolated)
        self.rag.clear()
        self.rag.index(raw_text, source_name=doc_path.stem)

        # 4b. Index supplementary context files
        for ctx_path in context_files or []:
            ctx_path = Path(ctx_path)
            try:
                ctx_text = load_document(ctx_path)
                self.rag.index(ctx_text, source_name=ctx_path.stem)
            except Exception as exc:
                console.print(
                    f"  [yellow]Skipping context file {ctx_path.name}: {exc}[/yellow]"
                )

        # 5. Generate per chapter
        cache_dir = self.output_dir / ".cache"
        cache_dir.mkdir(exist_ok=True)

        targets = (
            chapters
            if only_chapter is None
            else [ch for ch in chapters if int(ch["num"].split(".")[0]) == only_chapter]
        )

        generated = self._generate_all(
            targets, doc_subject, cache_dir, resume_from, on_progress, workers
        )

        # 6. Answer key (optional)
        if with_answers:
            if on_progress:
                on_progress(len(targets), len(targets), "Generating answer key...")
            console.print("[cyan]Generating answer key...[/cyan]")
            answer_key = self._generate_answer_key(generated, doc_subject)
            safe = re.sub(r"[^\w\s-]", "", doc_subject).strip().replace(" ", "_")
            ak_path = self.output_dir / f"{safe}_Answer_Key.md"
            ak_path.write_text(answer_key, encoding="utf-8")
            console.print(f"[green]Answer Key[/green] -> {ak_path}")

        # 7. Export
        combined = "\n\n---\n\n".join(generated)
        safe_name = re.sub(r"[^\w\s-]", "", doc_subject).strip().replace(" ", "_")
        from .export import export_all

        return export_all(
            combined,
            self.output_dir,
            base_name=f"{safe_name}_Practice_Guide",
            theme=theme,
        )

    # -- Generation (sequential or parallel) -----------------------------------

    def _generate_all(
        self,
        targets: list[Chapter],
        subject: str,
        cache_dir: Path,
        resume_from: int,
        on_progress: ProgressCallback,
        workers: int,
    ) -> list[str]:
        """Generate all target chapters, sequentially or in parallel."""

        def _gen_one(idx: int, ch: Chapter) -> tuple[int, str]:
            ch_num = ch["num"]
            cache_file = cache_dir / f"ch{ch_num.replace('.', '_')}.md"
            if int(ch_num.split(".")[0]) < resume_from and cache_file.exists():
                return idx, cache_file.read_text(encoding="utf-8")
            content = self._generate_chapter_with_retry(ch, subject)
            cache_file.write_text(content, encoding="utf-8")
            return idx, content

        generated = [""] * len(targets)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Generating chapters...", total=len(targets))

            if workers > 1 and len(targets) > 1:
                console.print(f"[cyan]Parallel mode: {workers} workers[/cyan]")
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures = [
                        pool.submit(_gen_one, i, ch) for i, ch in enumerate(targets)
                    ]
                    for future in futures:
                        idx, content = future.result()
                        generated[idx] = content
                        msg = f"Completed chapter {idx + 1} of {len(targets)}"
                        if on_progress:
                            on_progress(idx + 1, len(targets), msg)
                        progress.advance(task)
            else:
                for idx, ch in enumerate(targets):
                    msg = f"Generating chapter {idx + 1} of {len(targets)}: {ch['title'][:40]}"
                    if on_progress:
                        on_progress(idx, len(targets), msg)
                    progress.update(
                        task, description=f"Ch {ch['num']}: {ch['title'][:40]}..."
                    )

                    _, content = _gen_one(idx, ch)
                    generated[idx] = content
                    progress.advance(task)

                    if ch is not targets[-1]:
                        time.sleep(self.rate_limit_seconds)

        return generated

    # -- Chapter generation ----------------------------------------------------

    def _generate_chapter_with_retry(
        self, chapter: Chapter, subject: str, max_retries: int = 1
    ) -> str:
        """Generate a chapter, auto-retry once on validation failure."""
        content = self._generate_chapter(chapter, subject)
        result = validate_chapter(content, label=f"Ch {chapter['num']}")

        if result.passed or max_retries < 1:
            if not result.passed:
                console.print(
                    f"  [yellow]Ch {chapter['num']} validation:[/yellow] {result.summary()}"
                )
            return content

        console.print(
            f"  [yellow]Ch {chapter['num']} failed validation ({result.summary()}) -- retrying...[/yellow]"
        )
        time.sleep(self.rate_limit_seconds)
        content = self._generate_chapter(chapter, subject, temperature=0.5)
        retry_result = validate_chapter(content, label=f"Ch {chapter['num']}")
        if not retry_result.passed:
            console.print(
                f"  [yellow]Ch {chapter['num']} retry still has issues:[/yellow] {retry_result.summary()}"
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

        # Subject-type detection for format hints
        subject_type = detect_subject_type(subject)
        format_hint = example_format_hint(subject_type)

        # Fill template
        filled_template = (
            CHAPTER_TEMPLATE.replace("{chapter_num}", chapter["num"])
            .replace("{chapter_title}", chapter["title"])
            .replace("{subject}", subject)
            .replace("{subchapters}", sub_label)
        )

        prompt = f"""You are an expert educator and technical writer.
Generate a complete, high-quality practice guide chapter.
Fill every placeholder with accurate, practical, subject-specific content.
Do NOT add, remove, or rename any section. Do NOT output anything outside the template.

<subject>{subject}</subject>
<subject_type>{subject_type}</subject_type>
<chapter_number>{chapter["num"]}</chapter_number>
<chapter_title>{chapter["title"]}</chapter_title>
<subchapters>{sub_label}</subchapters>

<document_context>
{chapter["text"][:3000]}
</document_context>

<rag_context>
{rag_ctx}
</rag_context>

<web_research>
{web_ctx}
</web_research>

<format_instructions>
{format_hint}
</format_instructions>

<template>
{filled_template}
</template>

<rules>
- Use the exact subject "{subject}" throughout -- no generic placeholders
- Examples must use the format described in format_instructions
- All 10 quiz questions must be filled in with real questions
- Keep examples practical and realistic, not toy/trivial examples
- Do not reproduce the placeholder text -- replace it entirely
- Output ONLY the filled template, nothing else
</rules>"""

        try:
            resp = self._llm_call_with_backoff(prompt=prompt, temperature=temperature)
            content = resp.strip()
            # Strip accidental markdown fences
            content = re.sub(r"^```(?:markdown)?\n?", "", content)
            content = re.sub(r"\n```$", "", content)
            return content
        except Exception as exc:
            console.print(f"  [red]LLM error ch {chapter['num']}: {exc}[/red]")
            return (
                f"# Chapter {chapter['num']}: {chapter['title']}\n\n"
                f"<!-- Generation failed: {exc} -->\n"
            )

    def _llm_call_with_backoff(
        self, prompt: str, temperature: float = 0.3, max_attempts: int = 4
    ) -> str:
        """Call the LLM with exponential backoff on 429 rate-limit errors."""
        for attempt in range(max_attempts):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=4500,
                )
                return resp.choices[0].message.content.strip()
            except Exception as exc:
                if "429" in str(exc) and attempt < max_attempts - 1:
                    wait = self.rate_limit_seconds * (2**attempt)
                    console.print(
                        f"  [yellow]Rate limited, waiting {wait}s before retry...[/yellow]"
                    )
                    time.sleep(wait)
                else:
                    raise

    # -- Answer key generation -------------------------------------------------

    def _generate_answer_key(self, chapter_contents: list[str], subject: str) -> str:
        """Generate an answer key from all chapter quiz questions and exercises."""
        sections = []
        for content in chapter_contents:
            for heading in ("Chapter Quiz", "Practice Exercises"):
                parts = re.split(rf"(?i)##\s*\d*\.?\s*{heading}", content)
                if len(parts) > 1:
                    section_text = parts[1].split("##")[0].strip()
                    sections.append(f"### {heading}\n{section_text}")

        if not sections:
            return f"# Answer Key -- {subject}\n\nNo quiz questions or exercises found."

        prompt = f"""You are an expert educator. Generate a complete answer key for the following quiz questions and practice exercises from a {subject} study guide.

For each question/exercise:
- Restate the question number
- Provide the correct answer with a brief explanation

QUESTIONS AND EXERCISES:
{chr(10).join(sections[:6000])}

Format as clean Markdown with clear numbering."""

        try:
            body = self._llm_call_with_backoff(prompt=prompt, temperature=0.2)
            return f"# Answer Key -- {subject}\n\n{body}"
        except Exception as exc:
            return f"# Answer Key -- {subject}\n\n<!-- Generation failed: {exc} -->"


# -- Helpers -------------------------------------------------------------------


def _infer_subject(doc_path: Path, text: str) -> str:
    """
    Guess the subject from the filename or first non-empty line of text.
    Falls back to the filename stem.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and len(stripped) < 100:
            return stripped
    return doc_path.stem.replace("_", " ").replace("-", " ").title()
