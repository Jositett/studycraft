"""
StudyCraft -- Audio Generator.

Generates audio guides from chapter text using configurable TTS engines.
Supports dependency injection for engine selection and automatic fallback.
"""

from __future__ import annotations

import time
from pathlib import Path

from rich.console import Console

from .tts_engines import (
    TTSEngine,
    get_engine,
    get_fallback_chain,
    list_available_engines,
)

console = Console()


class AudioGenerator:
    """
    Generates audio files from text using injected TTS engines.

    Usage:
        gen = AudioGenerator(engine_name="kitten", voice="Bella")
        gen.generate_chapter("Chapter 1 content...", "output/ch1.mp3")

    Or with fallback:
        gen = AudioGenerator(use_fallback=True)
        gen.generate_all_chapters(chapters, "output/audio/")
    """

    def __init__(
        self,
        engine_name: str | None = None,
        engine: TTSEngine | None = None,
        use_fallback: bool = True,
        voice: str | None = None,
        speed: float = 1.0,
        **engine_kwargs,
    ) -> None:
        """
        Initialize audio generator.

        Args:
            engine_name: Name of engine ('chatterbox', 'kitten', 'coqui', 'openrouter')
            engine: Pre-configured TTSEngine instance (takes precedence over engine_name)
            use_fallback: If True, try fallback chain when primary engine fails
            voice: Default voice/speaker name
            speed: Default playback speed multiplier
            **engine_kwargs: Passed to engine factory if engine_name is provided
        """
        self._voice = voice
        self._speed = speed
        self._use_fallback = use_fallback
        self._primary_engine = engine

        if engine is None and engine_name is not None:
            try:
                self._primary_engine = get_engine(engine_name, **engine_kwargs)
            except Exception as exc:
                console.print(f"[yellow]Failed to init {engine_name}: {exc}[/yellow]")
                self._primary_engine = None

        self._fallback_chain = get_fallback_chain() if use_fallback else []
        self._resolved_engine: TTSEngine | None = None  # cached after first success

    def _get_engine_excluding(self, tried: set) -> TTSEngine | None:
        """Get an available engine, skipping any already tried."""
        # Return cached engine if it worked before and hasn't been tried yet
        if self._resolved_engine and self._resolved_engine.name not in tried:
            return self._resolved_engine

        if (
            self._primary_engine
            and self._primary_engine.is_available()
            and self._primary_engine.name not in tried
        ):
            return self._primary_engine

        if not self._use_fallback:
            return None

        available = list_available_engines()
        for engine_name, kwargs in self._fallback_chain:
            if engine_name not in available:
                continue
            try:
                engine = get_engine(engine_name, **kwargs)
                if engine.is_available() and engine.name not in tried:
                    console.print(f"[dim]Using fallback engine: {engine.name}[/dim]")
                    return engine
            except Exception:
                continue

        return None

    def _get_engine(self, text: str, output_path: Path) -> TTSEngine | None:
        return self._get_engine_excluding(set())

    def generate_chapter(
        self,
        text: str,
        output_path: str | Path,
        voice: str | None = None,
        speed: float | None = None,
        chapter_num: str | None = None,
        _tried: set | None = None,
        **kwargs,
    ) -> Path | None:
        """
        Generate audio for a single chapter.

        Args:
            text: Chapter text to synthesize
            output_path: Path to save audio file
            voice: Override default voice
            speed: Override default speed
            chapter_num: Chapter number for progress display
            **kwargs: Additional engine-specific arguments

        Returns:
            Path to generated audio file, or None if generation failed
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        tried: set = _tried or set()

        # Pick an engine not yet tried this call
        engine = self._get_engine_excluding(tried)
        if engine is None:
            console.print("[red]No TTS engine available[/red]")
            return None

        label = f"Chapter {chapter_num}" if chapter_num else "Chapter"
        console.print(f"[cyan]Generating audio: {label} ({engine.name})[/cyan]")

        try:
            result = engine.synthesize(
                text=text,
                output_path=output_path,
                voice=voice or self._voice,
                speed=speed or self._speed,
                **kwargs,
            )
            # Cache the engine that worked so subsequent chapters skip re-probing
            self._resolved_engine = engine
            console.print(f"[green]Audio saved:[/green] {result}")
            return result
        except Exception as exc:
            console.print(f"[red]Audio generation failed ({engine.name}): {exc}[/red]")
            tried.add(engine.name)
            if self._use_fallback:
                return self.generate_chapter(
                    text, output_path, voice, speed, chapter_num, _tried=tried, **kwargs
                )
            return None

    def generate_all_chapters(
        self,
        chapters: list[dict],
        output_dir: str | Path,
        subject: str | None = None,
        on_progress=None,
    ) -> dict[str, Path]:
        """
        Generate audio for all chapters.

        Args:
            chapters: List of chapter dicts with 'num' and 'title' keys
            output_dir: Directory to save audio files
            subject: Subject name (for naming)
            on_progress: Callback(current, total, message)

        Returns:
            Dict mapping chapter numbers to output paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}
        total = len(chapters)

        for idx, ch in enumerate(chapters, 1):
            ch_num = ch.get("num", str(idx))
            ch_title = ch.get("title", f"Chapter {ch_num}")

            # Build safe filename
            safe_name = "".join(c for c in ch_title if c.isalnum() or c in " -_").strip()
            safe_name = safe_name.replace(" ", "_")[:50]
            output_path = output_dir / f"ch{ch_num.replace('.', '_')}_{safe_name}.mp3"

            if on_progress:
                on_progress(idx, total, f"Generating audio: {ch_title}")

            result = self.generate_chapter(
                text=ch.get("content", ""),
                output_path=output_path,
                chapter_num=ch_num,
            )

            if result:
                results[ch_num] = result

            # Rate limiting
            time.sleep(0.5)

        console.print(f"[green]Generated {len(results)}/{total} audio chapters[/green]")
        return results

    def generate_from_text(
        self,
        text: str,
        output_path: str | Path,
        prefix: str = "audio",
    ) -> Path | None:
        """
        Generate audio from arbitrary text (e.g., answer key).

        Args:
            text: Text to synthesize
            output_path: Directory or file path
            prefix: Filename prefix if output_path is a directory

        Returns:
            Path to generated audio file, or None if failed
        """
        output_path = Path(output_path)
        if output_path.is_dir():
            output_path = output_path / f"{prefix}.mp3"

        return self.generate_chapter(text, output_path)

    @property
    def current_engine(self) -> TTSEngine | None:
        """Return the currently active engine, if any."""
        if self._primary_engine and self._primary_engine.is_available():
            return self._primary_engine
        return None

    @property
    def available_engines(self) -> list[str]:
        """Return list of available engine names."""
        return list_available_engines()
