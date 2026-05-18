"""
StudyCraft – Core engine.

Orchestrates: document loading -> chapter detection -> RAG indexing
              -> web research -> LLM generation -> export.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
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

DEFAULT_MODEL = "openrouter/free"  # cspell:disable-line
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_GENERATION_FAILED = "<!-- Generation failed"


@dataclass
class RunOptions:
    """Options for a StudyCraft generation run."""

    subject: str | None = None
    resume_from: int = 1
    only_chapter: int | None = None
    with_answers: bool = False
    on_progress: ProgressCallback = None
    context_files: list[str | Path] | None = None
    workers: int = 1
    theme: str | None = None
    on_check_control: ControlCallback = None
    difficulty: str = "intermediate"
    with_audio: bool = False
    tts_engine: str | None = None
    tts_voice: str | None = None
    tts_speed: float | None = None
    with_video: bool = False
    video_model: str | None = None
    video_resolution: str | None = None


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

    def run(  # noqa: PLR0913
        self,
        document_path: str | Path,
        opts: RunOptions | None = None,
        **kwargs,
    ) -> dict[str, Path]:
        """
        Full pipeline: load -> detect -> index -> generate -> export.

        Args:
            document_path: Path to any supported document.
            opts: RunOptions dataclass with all generation options.
            **kwargs: Alternative to opts — pass options as keyword arguments.
        """
        # Merge opts and kwargs for backward compatibility
        if opts is None:
            opts = RunOptions(**{k: v for k, v in kwargs.items() if k in RunOptions.__dataclass_fields__})

        doc_path = Path(document_path)
        on_progress = opts.on_progress
        on_check_control = opts.on_check_control

        # 1. Load document
        raw_text = load_document(doc_path)
        if not raw_text.strip():
            raise ValueError("Document appears to be empty or unreadable.")

        # 2. Detect subject name
        doc_subject = opts.subject or _infer_subject(doc_path, raw_text)
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
        for ctx_path in opts.context_files or []:
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
            if opts.only_chapter is None
            else [ch for ch in chapters if int(ch["num"].split(".")[0]) == opts.only_chapter]
        )

        generated = self._generate_all(
            targets,
            doc_subject,
            cache_dir,
            opts.resume_from,
            on_progress,
            opts.workers,
            on_check_control,
            opts.difficulty,
        )

        # 6. Review pass — fix chapters with unfilled placeholders
        self._review_chapters(generated, doc_subject, targets, on_progress)

        # 7. Answer key (optional)
        if opts.with_answers:
            if on_progress:
                on_progress(len(targets), len(targets), "Generating answer key...")
            console.print("[cyan]Generating answer key...[/cyan]")
            answer_key = self._generate_answer_key(generated, doc_subject)
            safe = re.sub(r"[^\w\s-]", "", doc_subject).strip().replace(" ", "_")
            ak_path = self.output_dir / f"{safe}_Answer_Key.md"
            ak_path.write_text(answer_key, encoding="utf-8")
            console.print(f"[green]Answer Key[/green] -> {ak_path}")

        # 7b. Audio generation (optional)
        audio_paths = self._run_audio(
            generated, targets, doc_subject, on_progress,
            opts.with_audio, opts.tts_engine, opts.tts_voice, opts.tts_speed,
        )

        # 7c. Video generation (optional)
        video_paths = self._run_video(
            generated, targets, on_progress, opts.with_video,
            opts.video_model, opts.video_resolution, audio_paths,
        )

        # 8. Export
        combined = "\n\n---\n\n".join(generated)
        safe_name = re.sub(r"[^\w\s-]", "", doc_subject).strip().replace(" ", "_")
        from .export import export_all

        result = export_all(
            combined,
            self.output_dir,
            base_name=f"{safe_name}_Practice_Guide",
            theme=opts.theme,
        )

        # Add audio paths to result
        if audio_paths:
            result["audio"] = audio_paths

        # Add video paths to result
        if video_paths:
            result["video"] = video_paths

        return result

    # -- Post-generation helpers ------------------------------------------------

    def _review_chapters(
        self, generated: list[str], subject: str, targets: list, on_progress: ProgressCallback
    ) -> None:
        """Fix chapters with unfilled placeholders."""
        console.print("[cyan]Reviewing chapters...[/cyan]")
        for idx, content in enumerate(generated):
            if not content or _GENERATION_FAILED in content:
                continue
            try:
                result = validate_chapter(content, label=f"Ch {idx + 1}")
                if not result.passed and result.placeholder_count > 0:
                    if on_progress:
                        on_progress(len(targets), len(targets), f"Fixing chapter {idx + 1} placeholders...")
                    fixed = self._fix_placeholders(content, subject)
                    if fixed:
                        generated[idx] = fixed
                        console.print(f"  [green]Ch {idx + 1}: fixed placeholders[/green]")
            except Exception as exc:
                console.print(f"  [yellow]Ch {idx + 1} review skipped: {exc}[/yellow]")

    def _collect_valid_chapters(self, generated: list[str], targets: list) -> list[dict]:
        """Collect chapters that generated successfully."""
        chapters = []
        for idx, content in enumerate(generated):
            if content and _GENERATION_FAILED not in content:
                chapters.append({
                    "num": targets[idx]["num"],
                    "title": targets[idx].get("title", f"Chapter {targets[idx]['num']}"),
                    "content": content,
                })
        return chapters

    def _run_audio(
        self, generated: list[str], targets: list, subject: str,
        on_progress: ProgressCallback, with_audio: bool,
        tts_engine: str | None, tts_voice: str | None, tts_speed: float | None,
    ) -> dict:
        """Generate audio guide if requested."""
        if not with_audio:
            return {}
        if on_progress:
            on_progress(len(targets), len(targets), "Generating audio guide...")
        console.print("[cyan]Generating audio guide...[/cyan]")

        from .audio_generator import AudioGenerator

        audio_gen = AudioGenerator(
            engine_name=tts_engine or self._tts_engine_name,
            voice=tts_voice or self._tts_voice,
            speed=tts_speed or self._tts_speed,
        )
        audio_dir = self.output_dir / "audio"
        audio_paths = audio_gen.generate_all_chapters(
            chapters=self._collect_valid_chapters(generated, targets),
            output_dir=audio_dir,
            subject=subject,
            on_progress=on_progress,
        )
        console.print(f"[green]Audio guide:[/green] {len(audio_paths)} chapters -> {audio_dir}")
        return audio_paths

    def _run_video(
        self, generated: list[str], targets: list, on_progress: ProgressCallback,
        with_video: bool, video_model: str | None, video_resolution: str | None,
        audio_paths: dict,
    ) -> dict:
        """Generate video guide if requested."""
        if not with_video:
            return {}
        if on_progress:
            on_progress(len(targets), len(targets), "Generating video guide...")
        console.print("[cyan]Generating video guide...[/cyan]")

        from .video_generator import VideoGenerator

        video_gen = VideoGenerator(
            api_key=self.api_key,
            model=video_model or self._video_model,
            output_dir=self.output_dir / "videos",
            resolution=video_resolution or self._video_resolution,
        )
        video_paths = video_gen.generate_all_chapters(
            chapters=self._collect_valid_chapters(generated, targets),
            output_dir=self.output_dir / "videos",
            audio_paths=audio_paths or {},
            on_progress=on_progress,
        )
        console.print(
            f"[green]Video guide:[/green] {len(video_paths)} chapters -> "
            f"{self.output_dir / 'videos'}"
        )
        return video_paths

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
                self._generate_parallel(
                    targets, generated, _gen_one, workers, on_progress, on_check_control, progress, task
                )
            else:
                self._generate_sequential(
                    targets, generated, _gen_one, on_progress, on_check_control, progress, task
                )

        return generated

    def _generate_parallel(self, targets, generated, gen_fn, workers, on_progress, on_check_control, progress, task):
        console.print(f"[cyan]Parallel mode: {workers} workers[/cyan]")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(gen_fn, i, ch) for i, ch in enumerate(targets)]
            for future in futures:
                idx, content = future.result()
                generated[idx] = content
                if on_progress:
                    on_progress(idx + 1, len(targets), f"Completed chapter {idx + 1} of {len(targets)}")
                progress.advance(task)
                if on_check_control and on_check_control() == "stop":
                    pool.shutdown(wait=False, cancel_futures=True)
                    console.print("[yellow]Generation stopped by user[/yellow]")
                    break

    def _generate_sequential(self, targets, generated, gen_fn, on_progress, on_check_control, progress, task):
        for idx, ch in enumerate(targets):
            if on_progress:
                on_progress(idx, len(targets), f"Generating chapter {idx + 1} of {len(targets)}: {ch['title'][:40]}")
            progress.update(task, description=f"Ch {ch['num']}: {ch['title'][:40]}...")

            _, content = gen_fn(idx, ch)
            generated[idx] = content
            progress.advance(task)

            if on_progress:
                on_progress(idx + 1, len(targets), f"Completed chapter {idx + 1} of {len(targets)}")
            if on_check_control and on_check_control() == "stop":
                console.print("[yellow]Generation stopped by user[/yellow]")
                break
            if ch is not targets[-1]:
                time.sleep(self.rate_limit_seconds)

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
        
        # Count placeholders to track completion
        placeholder_count = len(re.findall(r'\[(?:[A-Z][a-zA-Z\s\d]*\.{0,3}|\.{3})\]', filled_template))
        
        return f"""You are an expert educator and technical writer creating a complete, high-quality practice guide chapter.

CRITICAL: Your output MUST fill EVERY placeholder with accurate, subject-specific content.
This chapter contains {placeholder_count} placeholders (patterns like [Term 1], [Actionable objective 1], [...]).
EVERY SINGLE placeholder must be replaced with real content before you finish.

<subject>{subject}</subject>
<subject_type>{subject_type}</subject_type>
<chapter_number>{chapter["num"]}</chapter_number>
<chapter_title>{chapter["title"]}</chapter_title>
<subchapters>{sub_label}</subchapters>

<document_context>
{chapter["text"][:2500]}
</document_context>

<rag_context>
{rag_ctx[:1500]}
</rag_context>

<web_research>
{web_ctx[:1500]}
</web_research>

<format_instructions>
{format_hint}
</format_instructions>

<difficulty>
{diff_hint}
</difficulty>

<required_sections>
Your output MUST include all 8 sections:
1. Learning Objectives (5 objectives)
2. Core Concepts & Theory
3. Worked Examples (minimum 3 examples, each with Problem → Solution → Explanation)
4. Practice Exercises (Basic, Intermediate, Challenge levels)
5. Mini Project (with requirements and extension)
6. Chapter Quiz (exactly 10 questions)
7. Reflection (5 reflection questions)
8. Tips & Common Mistakes (3+ mistakes with explanations)

Do NOT skip or combine any sections.
</required_sections>

<template>
{filled_template}
</template>

<rules>
1. REPLACE every bracket placeholder [like this] with real, practical content for the subject "{subject}"
2. Do NOT output [Placeholder], [...], or any unfilled bracket content
3. Keep all section headings and structure exactly as shown in template
4. Examples must use the format: Problem → Solution (code/formula/approach) → Explanation
5. All 10 quiz questions MUST be filled and diverse (recall, conceptual, application, synthesis)
6. Do NOT add sections, remove sections, or rename section headings
7. Do NOT add any text before the first "# 📖" or after the last section
8. Output ONLY the filled template -- nothing else
9. Use {subject} as the specific subject throughout, not generic content
10. If you run out of tokens, you FAILED. Prioritize completeness of sections over length of content per section.
</rules>

Proceed to fill every placeholder and generate the complete chapter:"""

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
                f"{_GENERATION_FAILED}: {exc} -->\n"
            )

    def _llm_call_with_backoff(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_attempts: int = 4,
        timeout: int = 90,
        wall_timeout: int = 180,
    ) -> str:
        """Call the LLM with exponential backoff, wall-clock timeout, and auto model switching."""
        last_exc = None
        truncations = 0
        empty_count = 0
        for attempt in range(max_attempts):
            try:
                resp = self._call_with_wall_timeout(prompt, temperature, timeout, wall_timeout)
                content = resp.choices[0].message.content
                empty_count, should_continue = self._handle_empty_response(content, empty_count)
                if should_continue:
                    continue
                if content:
                    return content.strip()
            except BaseException as exc:
                last_exc = exc
                prompt, truncations = self._handle_llm_error(
                    exc, attempt, max_attempts, prompt, truncations
                )
                if prompt is None:
                    raise
        raise last_exc  # type: ignore[misc]

    def _handle_empty_response(self, content: str | None, empty_count: int) -> tuple[int, bool]:
        """Handle empty LLM responses. Returns (updated_count, should_continue)."""
        if content and content.strip():
            return empty_count, False
        empty_count += 1
        if empty_count >= 2:
            console.print(f"  [yellow]Model {self.model} returns empty — switching[/yellow]")
            if self._try_switch_model():
                return 0, True
            raise ValueError("LLM returned empty response after retries")
        console.print(f"  [yellow]Empty response, retrying in {self.rate_limit_seconds}s...[/yellow]")
        time.sleep(self.rate_limit_seconds)
        return empty_count, True

    def _call_with_wall_timeout(self, prompt: str, temperature: float, timeout: int, wall_timeout: int):
        """Execute a single LLM call with a hard wall-clock deadline."""
        from concurrent.futures import ThreadPoolExecutor as _TPE

        # Capture current values to avoid closure-over-loop-variable issues
        _prompt, _temp, _timeout = prompt, temperature, timeout

        def _do_call(_p=_prompt, _t=_temp, _to=_timeout):
            return self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": _p}],
                temperature=_t,
                max_tokens=4500,
                timeout=_to,
            )

        with _TPE(max_workers=1) as pool:
            future = pool.submit(_do_call)
            try:
                return future.result(timeout=wall_timeout)
            except (FuturesTimeout, TimeoutError):
                future.cancel()
                raise TimeoutError(f"LLM call exceeded {wall_timeout}s wall-clock timeout")

    def _handle_llm_error(
        self, exc: BaseException, attempt: int, max_attempts: int, prompt: str, truncations: int
    ) -> tuple[str | None, int]:
        """Handle LLM errors with retry logic. Returns (prompt, truncations) or (None, _) to re-raise."""
        err = str(exc)
        if "401" in err:
            return None, truncations
        if "must derive from BaseException" in err or not isinstance(exc, Exception):
            console.print(f"  [yellow]Model {self.model} internal error — switching[/yellow]")
            if self._try_switch_model():
                return prompt, truncations
            raise RuntimeError(f"LLM internal error: {err}") from exc

        is_retryable = self._is_retryable_error(err)
        if is_retryable and attempt < max_attempts - 1:
            wait = self.rate_limit_seconds * (2 ** attempt)
            console.print(f"  [yellow]Error {err[:60]}... waiting {wait}s[/yellow]")
            time.sleep(wait)
            return prompt, truncations
        if "400" in err and truncations < 2 and len(prompt) > 500:
            console.print("  [yellow]400 error, truncating prompt and retrying...[/yellow]")
            time.sleep(self.rate_limit_seconds)
            return prompt[: len(prompt) * 2 // 3], truncations + 1
        if ("404" in err or "503" in err or attempt == max_attempts - 1) and attempt < max_attempts - 1:
            if self._try_switch_model():
                return prompt, truncations
        return None, truncations

    @staticmethod
    def _is_retryable_error(err: str) -> bool:
        """Check if an error string indicates a retryable condition."""
        is_json_err = "Expecting value" in err or "JSONDecodeError" in err or "json" in err.lower()
        return "429" in err or "500" in err or "502" in err or "503" in err or is_json_err

    def _try_switch_model(self) -> bool:
        """Attempt to switch to the next verified fallback model. Returns True if switched."""
        if self._switches_used >= self._max_model_switches:
            return False

        from .model_registry import get_fallback_chain, test_model

        self._fallback_chain = get_fallback_chain(self.api_key)
        self._model_failures[self.model] = self._model_failures.get(self.model, 0) + 1

        for candidate in self._fallback_chain:
            if candidate == self.model or self._model_failures.get(candidate, 0) >= 1:
                continue
            if not self._probe_candidate(candidate, test_model):
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

    def _probe_candidate(self, candidate: str, test_fn) -> bool:
        """Probe a candidate model. Returns True if healthy."""
        console.print(f"  [dim]Probing candidate model: {candidate}...[/dim]")
        try:
            if not test_fn(self.api_key, candidate):
                console.print(f"  [yellow]Candidate {candidate} failed probe, skipping[/yellow]")
                self._model_failures[candidate] = 2
                return False
        except Exception:
            self._model_failures[candidate] = 2
            return False
        return True

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
        """Generate an answer key in batches to avoid overwhelming free models."""
        sections = self._extract_answer_sections(chapter_contents)
        if not sections:
            return f"# Answer Key -- {subject}\n\nNo quiz questions or exercises found."

        all_answers = self._generate_answer_batches(sections, subject)
        body = "\n\n---\n\n".join(all_answers) if all_answers else "Generation failed."
        return f"# Answer Key -- {subject}\n\n{body}"

    @staticmethod
    def _extract_answer_sections(chapter_contents: list[str]) -> list[str]:
        """Extract quiz and exercise sections from generated chapters."""
        sections = []
        for content in chapter_contents:
            if not content or _GENERATION_FAILED in content:
                continue
            for heading in ("Chapter Quiz", "Practice Exercises"):
                parts = re.split(rf"(?i)##\s*\d*\.?\s*{heading}", content)
                if len(parts) > 1:
                    section_text = parts[1].split("##")[0].strip()
                    sections.append(f"### {heading}\n{section_text}")
        return sections

    def _generate_answer_batches(self, sections: list[str], subject: str) -> list[str]:
        """Generate answers in batches of 6 sections."""
        batch_size = 6
        all_answers: list[str] = []
        for i in range(0, len(sections), batch_size):
            batch = [s[:1200] for s in sections[i : i + batch_size]]
            combined = "\n\n".join(batch)
            prompt = (
                f"You are an expert educator. Generate answers for these "
                f"{subject} quiz questions and exercises.\n\n"
                f"For each question: restate the number, give the correct answer "
                f"with a brief explanation.\n\n"
                f"QUESTIONS:\n{combined}\n\n"
                f"Format as clean Markdown."
            )
            try:
                body = self._llm_call_with_backoff(prompt=prompt, temperature=0.2, wall_timeout=120)
                if body and _GENERATION_FAILED not in body:
                    all_answers.append(body)
            except Exception as exc:
                all_answers.append(f"<!-- Batch {i // batch_size + 1} failed: {exc} -->")
                console.print(f"  [yellow]Answer key batch {i // batch_size + 1} failed: {exc}[/yellow]")
            time.sleep(self.rate_limit_seconds)
        return all_answers


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
