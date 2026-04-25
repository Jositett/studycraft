"""
StudyCraft -- Video Composer.

Composes final videos by combining:
  - Generated video content (from OpenRouter)
  - TTS audio narration (from audio_generator)
  - Text overlays (chapter titles, key points)
  - Theme-based styling
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

console = Console()


class VideoComposer:
    """
    Composes final videos with audio and text overlays.

    Uses videopython (if available) or falls back to basic composition.
    """

    def __init__(
        self,
        output_dir: str | Path = "output/videos",
        theme: str | None = None,
    ) -> None:
        """
        Initialize video composer.

        Args:
            output_dir: Directory to save composed videos
            theme: Theme name for styling (uses studycraft themes)
        """
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._theme = theme
        self._videopython_available = self._check_videopython()

    def _check_videopython(self) -> bool:
        """Check if videopython is available."""
        try:
            import videopython  # noqa: F401

            return True
        except ImportError:
            return False

    def compose_chapter_video(
        self,
        video_path: Path,
        audio_path: Path | None = None,
        chapter_title: str | None = None,
        output_path: Path | None = None,
    ) -> Path | None:
        """
        Compose final video with audio and text overlays.

        Args:
            video_path: Path to generated video file
            audio_path: Path to TTS audio file (optional)
            chapter_title: Chapter title for text overlay
            output_path: Output path (defaults to same dir)

        Returns:
            Path to composed video, or None if failed
        """
        if not video_path.exists():
            console.print(f"[red]Video file not found: {video_path}[/red]")
            return None

        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_composed{video_path.suffix}"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Fallback: if no videopython, just copy video with audio using ffmpeg
        if not self._videopython_available:
            console.print("[yellow]videopython not available, using ffmpeg fallback[/yellow]")
            return self._compose_with_ffmpeg(video_path, audio_path, output_path)

        try:
            from videopython import Video

            # Load video
            video = Video.from_path(str(video_path))

            # Add audio if provided
            if audio_path and audio_path.exists():
                video = video.add_audio_from_file(str(audio_path))
                console.print("[dim]Added audio to video[/dim]")

            # Add title overlay if provided
            if chapter_title:
                video = video.add_text(
                    text=chapter_title,
                    position=("center", "top"),
                    duration=3.0,
                    font_size=48,
                    color="white",
                    background_color="rgba(0,0,0,0.5)",
                )
                console.print("[dim]Added title overlay[/dim]")

            # Save composed video
            video.save(str(output_path))
            console.print(f"[green]Composed video saved:[/green] {output_path}")

            return output_path

        except Exception as exc:
            console.print(f"[red]Video composition failed: {exc}[/red]")
            # Fallback to original video
            output_path.write_bytes(video_path.read_bytes())
            return output_path

    def _compose_with_ffmpeg(
        self,
        video_path: Path,
        audio_path: Path | None,
        output_path: Path,
    ) -> Path:
        """Fallback composition using ffmpeg directly."""
        import subprocess

        cmd = ["ffmpeg", "-y", "-i", str(video_path)]

        if audio_path and audio_path.exists():
            cmd.extend(["-i", str(audio_path), "-c", "copy", "-shortest"])

        cmd.append(str(output_path))

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            console.print(f"[green]Composed with ffmpeg:[/green] {output_path}")
            return output_path
        except subprocess.CalledProcessError as exc:
            console.print(f"[red]ffmpeg failed: {exc}[/red]")
            # Return original video
            output_path.write_bytes(video_path.read_bytes())
            return output_path

    def compose_all_chapters(
        self,
        video_paths: dict[str, Path],
        audio_paths: dict[str, Path] | None = None,
        chapters: list[dict] | None = None,
    ) -> dict[str, Path]:
        """
        Compose videos for all chapters.

        Args:
            video_paths: Dict mapping chapter numbers to video paths
            audio_paths: Dict mapping chapter numbers to audio paths
            chapters: List of chapter dicts with 'num' and 'title' keys

        Returns:
            Dict mapping chapter numbers to composed video paths
        """
        results = {}
        total = len(video_paths)

        for idx, (ch_num, vid_path) in enumerate(video_paths.items(), 1):
            console.print(f"[cyan]Composing video {idx}/{total}: Chapter {ch_num}[/cyan]")

            audio_path = None
            if audio_paths and ch_num in audio_paths:
                audio_path = audio_paths[ch_num]

            chapter_title = None
            if chapters:
                for ch in chapters:
                    if ch.get("num") == ch_num:
                        chapter_title = ch.get("title")
                        break

            result = self.compose_chapter_video(
                video_path=vid_path,
                audio_path=audio_path,
                chapter_title=chapter_title,
            )

            if result:
                results[ch_num] = result

        console.print(f"[green]Composed {len(results)}/{total} chapter videos[/green]")
        return results
