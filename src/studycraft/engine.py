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
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from .detector import Chapter, chapters_to_outline, detect_chapters
from .loader import load_document
from .rag import RAGIndex
from .researcher import research
from .template import (
    CHAPTER_TEMPLATE,
    detect_subject_type,
    difficulty_hint,
    example_format_hint,
)
from .validator import validate_chapter

console = Console()

# Type alias for progress callbacks: (current, total, message) -> None
ProgressCallback = Callable[[int, int, str], None] | None
ControlCallback = Callable[[], str | None] | None

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
        tts_engine: str | None = None,
        tts_voice: str | None = None,
        tts_speed: float = 1.0,
        video_model: str | None = None,
        video_resolution: str = "720p",
    ) -> None:
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.api_key = api_key
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit_seconds = rate_limit_seconds
        self.rag = RAGIndex(persist_dir=rag_dir)
        self._fallback_chain: list[str] = []
        self._model_failures: dict[str, int] = {}
        self._max_model_switches = 5
        self._switches_used = 0

        # TTS support
        self._tts_engine_name = tts_engine
        self._tts_voice = tts_voice
        self._tts_speed = tts_speed
        self._audio_gen = None

        # Video support
        self._video_model = video_model
        self._video_resolution = video_resolution
        self._video_gen = None

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
        on_check_control: ControlCallback = None,
        difficulty: str = "intermediate",
        with_audio: bool = False,
        tts_engine: str | None = None,
        tts_voice: str | None = None,
        tts_speed: float | None = None,
        with_video: bool = False,
        video_model: str | None = None,
        video_resolution: str | None = None,
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
            with_audio: Generate audio guide using TTS.
            tts_engine: TTS engine name (kitten, chatterbox, coqui, openrouter).
            tts_voice: Voice name (engine-specific).
            tts_speed: Playback speed multiplier.
            with_video: Generate video guide using OpenRouter (free models only).
            video_model: Video generation model ID (must be free).
            video_resolution: Video resolution (720p or 1080p).
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
        chapters = detect_chapters(raw_text, llm_client=self.client)
        if not chapters:
            raise ValueError("Could not detect any chapters. Check the document format.")

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
                console.print(f"  [yellow]Skipping context file {ctx_path.name}: {exc}[/yellow]")

        # 5. Generate per chapter
        cache_dir = self.output_dir / ".cache"
        cache_dir.mkdir(exist_ok=True)

        targets = (
            chapters
            if only_chapter is None
            else [ch for ch in chapters if int(ch["num"].split(".")[0]) == only_chapter]
        )

        generated = self._generate_all(
            targets,
            doc_subject,
            cache_dir,
            resume_from,
            on_progress,
            workers,
            on_check_control,
            difficulty,
        )

        # 6. Review pass — fix chapters with unfilled placeholders
        console.print("[cyan]Reviewing chapters...[/cyan]")
        for idx, content in enumerate(generated):
            if not content or "<!-- Generation failed" in content:
                continue
            try:
                result = validate_chapter(content, label=f"Ch {idx + 1}")
                if not result.passed and result.placeholder_count > 0:
                    if on_progress:
                        on_progress(
                            len(targets),
                            len(targets),
                            f"Fixing chapter {idx + 1} placeholders...",
                        )
                    fixed = self._fix_placeholders(content, doc_subject)
                    if fixed:
                        generated[idx] = fixed
                        console.print(f"  [green]Ch {idx + 1}: fixed placeholders[/green]")

            except Exception as exc:
                console.print(f"  [yellow]Ch {idx + 1} review skipped: {exc}[/yellow]")

        # 7. Answer key (optional)
        if with_answers:
            if on_progress:
                on_progress(len(targets), len(targets), "Generating answer key...")
            console.print("[cyan]Generating answer key...[/cyan]")
            answer_key = self._generate_answer_key(generated, doc_subject)
            safe = re.sub(r"[^\w\s-]", "", doc_subject).strip().replace(" ", "_")
            ak_path = self.output_dir / f"{safe}_Answer_Key.md"
            ak_path.write_text(answer_key, encoding="utf-8")
            console.print(f"[green]Answer Key[/green] -> {ak_path}")

        # 7b. Audio generation (optional)
        audio_paths = {}
        if with_audio:
            if on_progress:
                on_progress(len(targets), len(targets), "Generating audio guide...")
            console.print("[cyan]Generating audio guide...[/cyan]")

            from .audio_generator import AudioGenerator

            engine_name = tts_engine or self._tts_engine_name
            voice = tts_voice or self._tts_voice
            speed = tts_speed or self._tts_speed

            audio_gen = AudioGenerator(
                engine_name=engine_name,
                voice=voice,
                speed=speed,
            )

            # Prepare chapters for audio generation
            audio_chapters = []
            for idx, content in enumerate(generated):
                if content and "<!-- Generation failed" not in content:
                    audio_chapters.append(
                        {
                            "num": targets[idx]["num"],
                            "title": targets[idx].get("title", f"Chapter {targets[idx]['num']}"),
                            "content": content,
                        }
                    )

            audio_dir = self.output_dir / "audio"
            audio_paths = audio_gen.generate_all_chapters(
                chapters=audio_chapters,
                output_dir=audio_dir,
                subject=doc_subject,
                on_progress=on_progress,
            )
            console.print(f"[green]Audio guide:[/green] {len(audio_paths)} chapters -> {audio_dir}")

        # 7c. Video generation (optional)
        video_paths = {}
        if with_video:
            if on_progress:
                on_progress(len(targets), len(targets), "Generating video guide...")
            console.print("[cyan]Generating video guide...[/cyan]")

            from .video_generator import VideoGenerator

            v_model = video_model or self._video_model

            video_gen = VideoGenerator(
                api_key=self.api_key,
                model=v_model,
                output_dir=self.output_dir / "videos",
            )

            # Prepare chapters for video generation
            video_chapters = []
            for idx, content in enumerate(generated):
                if content and "<!-- Generation failed" not in content:
                    video_chapters.append(
                        {
                            "num": targets[idx]["num"],
                            "title": targets[idx].get("title", f"Chapter {targets[idx]['num']}"),
                            "content": content,
                        }
                    )

            video_paths = video_gen.generate_all_chapters(
                chapters=video_chapters,
                output_dir=self.output_dir / "videos",
                on_progress=on_progress,
            )
            console.print(
                f"[green]Video guide:[/green] {len(video_paths)} chapters -> "
                f"{self.output_dir / 'videos'}"
            )

        # 8. Export
        combined = "\n\n---\n\n".join(generated)
        safe_name = re.sub(r"[^\w\s-]", "", doc_subject).strip().replace(" ", "_")
        from .export import export_all

        result = export_all(
            combined,
            self.output_dir,
            base_name=f"{safe_name}_Practice_Guide",
            theme=theme,
        )

        # Add audio paths to result
        if audio_paths:
            result["audio"] = audio_paths

        # Add video paths to result
        if video_paths:
            result["video"] = video_paths

        return result

    # -- Generation (sequential or parallel) -----------------------------------

    def _generate_all(
        self,
        targets: list[Chapter],
        subject: str,
        cache_dir: Path,
        resume_from: int,
        on_progress: ProgressCallback,
        workers: int,
        on_check_control: ControlCallback = None,
        difficulty: str = "intermediate",
    ) -> list[str]:
        """Generate all target chapters, sequentially or in parallel."""

        def _gen_one(idx: int, ch: Chapter) -> tuple[int, str]:
            ch_num = ch["num"]
            cache_file = cache_dir / f"ch{ch_num.replace('.', '_')}.md"
            if int(ch_num.split(".")[0]) < resume_from and cache_file.exists():
                return idx, cache_file.read_text(encoding="utf-8")
            content = self._generate_chapter_with_retry(ch, subject, difficulty=difficulty)
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
                    futures = [pool.submit(_gen_one, i, ch) for i, ch in enumerate(targets)]
                    for future in futures:
                        idx, content = future.result()
                        generated[idx] = content
                        msg = f"Completed chapter {idx + 1} of {len(targets)}"
                        if on_progress:
                            on_progress(idx + 1, len(targets), msg)
                        progress.advance(task)

                        # Check for pause/stop (pause handled by blocking callback)
                        if on_check_control:
                            signal = on_check_control()
                            if signal == "stop":
                                pool.shutdown(wait=False, cancel_futures=True)
                                console.print("[yellow]Generation stopped by user[/yellow]")
                                break
            else:
                for idx, ch in enumerate(targets):
                    msg = f"Generating chapter {idx + 1} of {len(targets)}: {ch['title'][:40]}"
                    if on_progress:
                        on_progress(idx, len(targets), msg)
                    progress.update(task, description=f"Ch {ch['num']}: {ch['title'][:40]}...")

                    _, content = _gen_one(idx, ch)
                    generated[idx] = content
                    progress.advance(task)

                    if on_progress:
                        on_progress(
                            idx + 1,
                            len(targets),
                            f"Completed chapter {idx + 1} of {len(targets)}",
                        )

                    # Check for pause/stop
                    if on_check_control:
                        signal = on_check_control()
                        if signal == "stop":
                            console.print("[yellow]Generation stopped by user[/yellow]")
                            break

                    if ch is not targets[-1]:
                        time.sleep(self.rate_limit_seconds)

        return generated

    # -- Chapter generation ----------------------------------------------------

    def _generate_chapter_with_retry(
        self,
        chapter: Chapter,
        subject: str,
        max_retries: int = 1,
        difficulty: str = "intermediate",
    ) -> str:
        """Generate a chapter, auto-retry once on validation failure."""
        content = self._generate_chapter(chapter, subject, difficulty=difficulty)
        result = validate_chapter(content, label=f"Ch {chapter['num']}")

        if result.passed or max_retries < 1:
            if not result.passed:
                console.print(
                    f"  [yellow]Ch {chapter['num']} validation:[/yellow] {result.summary()}"
                )
            return content

        console.print(
            f"  [yellow]Ch {chapter['num']} failed validation "
            f"({result.summary()}) -- retrying...[/yellow]"
        )
        time.sleep(self.rate_limit_seconds)

        # Total structural failure (>4 missing sections): switch model before retrying
        if len(result.missing_sections) > 4:
            console.print(
                f"  [yellow]Ch {chapter['num']} total failure — switching model before retry[/yellow]"
            )
            self._try_switch_model()

        content = self._generate_chapter(chapter, subject, temperature=0.5, difficulty=difficulty)
        retry_result = validate_chapter(content, label=f"Ch {chapter['num']}")
        if not retry_result.passed:
            console.print(
                f"  [yellow]Ch {chapter['num']} retry still has issues:[/yellow] {retry_result.summary()}"
            )
        return content

    def _build_prompt(
        self,
        chapter: Chapter,
        subject: str,
        rag_ctx: str,
        web_ctx: str,
        subject_type: str,
        format_hint: str,
        diff_hint: str,
    ) -> str:
        """Construct the LLM prompt for a chapter from its components."""
        sub_titles = [s["title"] for s in chapter["subchapters"]]
        sub_label = "\n".join(f"  - {t}" for t in sub_titles) if sub_titles else "None detected"
        filled_template = (
            CHAPTER_TEMPLATE.replace("{chapter_num}", chapter["num"])
            .replace("{chapter_title}", chapter["title"])
            .replace("{subject}", subject)
            .replace("{subchapters}", sub_label)
        )
        return f"""You are an expert educator and technical writer.
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

<difficulty>
{diff_hint}
</difficulty>

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

    def _generate_chapter(
        self,
        chapter: Chapter,
        subject: str,
        temperature: float = 0.3,
        difficulty: str = "intermediate",
    ) -> str:
        sub_titles = [s["title"] for s in chapter["subchapters"]]

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
        diff_hint = difficulty_hint(difficulty)

        prompt = self._build_prompt(
            chapter, subject, rag_ctx, web_ctx, subject_type, format_hint, diff_hint
        )

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
        self, prompt: str, temperature: float = 0.3, max_attempts: int = 4,
        timeout: int = 90,
    ) -> str:
        """Call the LLM with exponential backoff and auto model switching."""
        last_exc = None
        truncations = 0
        for attempt in range(max_attempts):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=4500,
                    timeout=timeout,
                )
                content = resp.choices[0].message.content
                # Empty response is transient — retry with backoff before switching
                if not content or not content.strip():
                    if attempt < max_attempts - 1:
                        wait = self.rate_limit_seconds * (2 ** attempt)
                        console.print(f"  [yellow]Empty response, retrying in {wait}s...[/yellow]")
                        time.sleep(wait)
                        continue
                    raise ValueError("LLM returned empty response after retries")
                return content.strip()
            except Exception as exc:
                last_exc = exc
                err = str(exc)
                # Never switch models on auth errors — surface them immediately
                if "401" in err:
                    raise
                retryable = "429" in err or "500" in err or "502" in err or "503" in err
                if retryable and attempt < max_attempts - 1:
                    wait = self.rate_limit_seconds * (2**attempt)
                    console.print(f"  [yellow]Error {err[:60]}... waiting {wait}s[/yellow]")
                    time.sleep(wait)
                elif "400" in err and truncations < 2 and len(prompt) > 500:
                    console.print("  [yellow]400 error, truncating prompt and retrying...[/yellow]")
                    prompt = prompt[: len(prompt) * 2 // 3]
                    truncations += 1
                    time.sleep(self.rate_limit_seconds)
                else:
                    # Only switch model for model-specific errors (404, 503) or after exhausting retries
                    if "404" in err or "503" in err or attempt == max_attempts - 1:
                        switched = self._try_switch_model()
                        if switched and attempt < max_attempts - 1:
                            continue
                    raise
        raise last_exc  # type: ignore[misc]

    def _try_switch_model(self) -> bool:
        """Attempt to switch to the next verified fallback model. Returns True if switched."""
        if self._switches_used >= self._max_model_switches:
            return False

        # Always re-fetch so we use the freshest health cache
        from .model_registry import get_fallback_chain, test_model

        self._fallback_chain = get_fallback_chain(self.api_key)

        # Track failures for current model
        self._model_failures[self.model] = self._model_failures.get(self.model, 0) + 1

        # Find next model not yet failed, and probe it before committing
        for candidate in self._fallback_chain:
            if candidate == self.model:
                continue
            if self._model_failures.get(candidate, 0) >= 2:
                continue
            console.print(f"  [dim]Probing candidate model: {candidate}...[/dim]")
            if not test_model(self.api_key, candidate):
                console.print(f"  [yellow]Candidate {candidate} failed probe, skipping[/yellow]")
                self._model_failures[candidate] = 2  # mark as bad
                continue
            old = self.model
            self.model = candidate
            self._switches_used += 1
            console.print(
                f"  [cyan]Switching model: {old} -> {self.model} "
                f"(switch {self._switches_used}/{self._max_model_switches})[/cyan]"
            )
            return True
        return False

    # -- Answer key generation -------------------------------------------------

    def _fix_placeholders(self, content: str, subject: str) -> str | None:
        """Targeted fix: replace unfilled [...] placeholders in a chapter."""
        prompt = (
            f"The following practice guide chapter for '{subject}' has unfilled "
            "placeholders marked with [...] brackets. Replace EVERY [...] placeholder "
            "with real, accurate, subject-specific content. Do NOT change any other text. "
            "Output the COMPLETE fixed chapter.\n\n"
            f"{content}"
        )
        try:
            fixed = self._llm_call_with_backoff(prompt=prompt, temperature=0.4)
            if fixed and "[...]" not in fixed and len(fixed) > len(content) * 0.5:
                return fixed
        except Exception:
            pass
        return None

    def _generate_answer_key(self, chapter_contents: list[str], subject: str) -> str:
        """Generate an answer key from all chapter quiz questions and exercises."""
        sections = []
        for content in chapter_contents:
            # Skip failed chapters — they have no usable quiz content
            if not content or "<!-- Generation failed" in content:
                continue
            for heading in ("Chapter Quiz", "Practice Exercises"):
                parts = re.split(rf"(?i)##\s*\d*\.?\s*{heading}", content)
                if len(parts) > 1:
                    section_text = parts[1].split("##")[0].strip()
                    sections.append(f"### {heading}\n{section_text}")

        if not sections:
            return f"# Answer Key -- {subject}\n\nNo quiz questions or exercises found."

        # Limit total content to avoid token overflow: max 20 sections, each capped at ~1500 chars
        capped_sections = [s[:1500] for s in sections[:20]]
        combined = "\n\n".join(capped_sections)
        prompt = (
            f"You are an expert educator. Generate a complete answer key for the following "
            f"quiz questions and practice exercises from a {subject} study guide.\n\n"
            f"For each question/exercise:\n"
            f"- Restate the question number\n"
            f"- Provide the correct answer with a brief explanation\n\n"
            f"QUESTIONS AND EXERCISES:\n{combined}\n\n"
            f"Format as clean Markdown with clear numbering."
        )

        try:
            body = self._llm_call_with_backoff(prompt=prompt, temperature=0.2)
            result = f"# Answer Key -- {subject}\n\n{body}"
            # Retry if result looks incomplete
            if len(result) < 200 or "<!-- Generation failed" in result:
                body = self._llm_call_with_backoff(prompt=prompt, temperature=0.3)
                result = f"# Answer Key -- {subject}\n\n{body}"
            return result
        except Exception:
            try:
                body = self._llm_call_with_backoff(prompt=prompt, temperature=0.3)
                return f"# Answer Key -- {subject}\n\n{body}"
            except Exception as exc:
                return f"# Answer Key -- {subject}\n\n<!-- Generation failed: {exc} -->"


# -- Helpers -------------------------------------------------------------------


def _infer_subject(doc_path: Path, text: str) -> str:
    """
    Guess the subject from the document text.
    Skips junk lines (page numbers, dates, short fragments).
    Falls back to the filename stem.
    """
    skip_patterns = re.compile(
        r"^(\d+|page\s*\d+|table of contents|copyright|all rights|isbn|\d{4}[-/]\d{2})",
        re.IGNORECASE,
    )
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or len(stripped) < 5 or len(stripped) > 100:
            continue
        if skip_patterns.match(stripped):
            continue
        # Skip lines that are mostly punctuation or numbers
        alpha = sum(1 for c in stripped if c.isalpha())
        if alpha < len(stripped) * 0.4:
            continue
        return stripped
    return doc_path.stem.replace("_", " ").replace("-", " ").title()
