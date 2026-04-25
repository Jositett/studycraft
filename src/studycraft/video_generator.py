"""
StudyCraft -- Video Generator.

Generates video content from chapter text using OpenRouter's video generation API.
Supports combining TTS audio with generated video content.
Falls back to audio-only when video generation is unavailable.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from rich.console import Console

from .model_registry import get_free_models, get_model

console = Console()

# OpenRouter Video API endpoints
_VIDEO_API_BASE = "https://openrouter.ai/api/v1/videos"
_POLL_INTERVAL = 30  # seconds between polling
_TIMEOUT = 600  # 10 minutes max wait


class VideoGenerator:
    """
    Generates video from text using OpenRouter's video generation API.

    Workflow: Submit job -> Poll status -> Download video
    Only uses free models (validated via model_registry).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "google/veo-3.1",
        base_url: str = _VIDEO_API_BASE,
        output_dir: str | Path = "output/videos",
    ) -> None:
        """
        Initialize video generator.

        Args:
            api_key: OpenRouter API key (or uses env var)
            model: Video generation model ID (must be free)
            base_url: OpenRouter video API base URL
            output_dir: Directory to save generated videos
        """
        from os import getenv

        self._api_key = api_key or getenv("OPENROUTER_API_KEY") or getenv("STUDYCRAFT_API_KEY")
        self._model = model
        self._base_url = base_url
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Check if the model is free; warn if it's a paid model
        try:
            model_info = get_model(self._model)
            if model_info and not model_info.get("is_free", False):
                console.print(
                    f"[yellow]⚠ Warning:[/yellow] Model '{self._model}' is not marked as free. "
                    f"You may incur costs when using this video generation model. "
                    f"Set STUDYCRAFT_VIDEO_MODEL to a free model to avoid charges."
                )
        except Exception:
            pass  # Silently ignore if model lookup fails

    def _check_free_model(self) -> bool:
        """Verify the configured model is free."""
        try:
            model_info = get_model(self._model)
            if model_info:
                return model_info.get("is_free", False)
            free_models = get_free_models()
            return any(m["id"] == self._model for m in free_models)
        except Exception:
            return False

    def _make_request(self, method: str, endpoint: str, data: dict | None = None) -> dict:
        """Make an HTTP request to the OpenRouter video API."""
        url = f"{self._base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        body = json.dumps(data).encode() if data else None
        req = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except URLError as exc:
            raise RuntimeError(f"API request failed: {exc}") from exc

    def generate_video(
        self,
        prompt: str,
        output_path: str | Path,
        duration: int = 5,
        resolution: str = "720p",
        aspect_ratio: str = "16:9",
        generate_audio: bool = True,
        chapter_num: str | None = None,
    ) -> Path | None:
        """
        Generate video from a text prompt.

        Args:
            prompt: Text description for video generation
            output_path: Path to save the video file
            duration: Video duration in seconds (4-10)
            resolution: Video resolution (720p or 1080p)
            aspect_ratio: Aspect ratio (16:9, 9:16, 1:1, etc.)
            generate_audio: Whether to generate audio with video
            chapter_num: Chapter number for progress display

        Returns:
            Path to generated video file, or None if failed
        """
        if not self._api_key:
            console.print("[red]No API key configured for video generation[/red]")
            return None

        if not self._check_free_model():
            console.print(
                f"[yellow]Model '{self._model}' is not free. "
                "Video generation only supports free models.[/yellow]"
            )
            return None

        label = f"Chapter {chapter_num}" if chapter_num else "Video"
        console.print(f"[cyan]Generating video: {label} ({self._model})[/cyan]")

        # Step 1: Submit video generation job
        payload = {
            "model": self._model,
            "prompt": prompt[:500],  # Limit prompt length
            "duration": duration,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "generate_audio": generate_audio,
        }

        try:
            response = self._make_request("POST", "", payload)
            job_id = response.get("id")
            polling_url = response.get("polling_url")

            if not job_id:
                console.print("[red]Failed to submit video job[/red]")
                return None

            console.print(f"[dim]Job submitted: {job_id}[/dim]")

            # Step 2: Poll for completion
            video_url = self._poll_job(job_id)

            if not video_url:
                console.print("[red]Video generation failed or timed out[/red]")
                return None

            # Step 3: Download video
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self._download_video(video_url, output_path)
            console.print(f"[green]Video saved:[/green] {output_path}")

            return output_path

        except Exception as exc:
            console.print(f"[red]Video generation error: {exc}[/red]")
            return None

    def _poll_job(self, job_id: str) -> str | None:
        """Poll job status until completion or timeout."""
        start_time = time.time()

        while time.time() - start_time < _TIMEOUT:
            try:
                status_resp = self._make_request("GET", f"/{job_id}")
                status = status_resp.get("status", "unknown")

                console.print(f"[dim]Status: {status}[/dim]")

                if status == "completed":
                    # Get download URL
                    unsigned_urls = status_resp.get("unsigned_urls", [])
                    if unsigned_urls:
                        return unsigned_urls[0]
                    return None
                elif status in ("failed", "cancelled", "expired"):
                    error = status_resp.get("error", "Unknown error")
                    console.print(f"[red]Job {status}: {error}[/red]")
                    return None

                time.sleep(_POLL_INTERVAL)

            except Exception as exc:
                console.print(f"[yellow]Polling error: {exc}[/yellow]")
                time.sleep(_POLL_INTERVAL)

        console.print("[red]Video generation timed out[/red]")
        return None

    def _download_video(self, url: str, output_path: Path) -> None:
        """Download video from URL."""
        req = Request(url)
        with urlopen(req, timeout=60) as resp:
            output_path.write_bytes(resp.read())

    def generate_chapter_video(
        self,
        chapter_text: str,
        chapter_num: str,
        chapter_title: str,
        output_dir: str | Path | None = None,
    ) -> Path | None:
        """
        Generate video for a single chapter.

        Args:
            chapter_text: Full chapter text
            chapter_num: Chapter number
            chapter_title: Chapter title
            output_dir: Override default output directory

        Returns:
            Path to generated video, or None if failed
        """
        output_dir = Path(output_dir) if output_dir else self._output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create a visual prompt from chapter content
        # Summarize first 200 words for video prompt
        words = chapter_text.split()[:200]
        visual_prompt = (
            f"Educational video about {chapter_title}. Key concepts: {' '.join(words[:50])}"
        )

        safe_title = "".join(c for c in chapter_title if c.isalnum() or c in " -_").strip()[:50]
        safe_title = safe_title.replace(" ", "_")

        output_path = output_dir / f"ch{chapter_num.replace('.', '_')}_{safe_title}.mp4"

        return self.generate_video(
            prompt=visual_prompt,
            output_path=output_path,
            chapter_num=chapter_num,
        )

    def generate_all_chapters(
        self,
        chapters: list[dict],
        output_dir: str | Path | None = None,
        on_progress=None,
    ) -> dict[str, Path]:
        """
        Generate videos for all chapters.

        Args:
            chapters: List of chapter dicts with 'num', 'title', 'content' keys
            output_dir: Override default output directory
            on_progress: Callback(current, total, message)

        Returns:
            Dict mapping chapter numbers to output paths
        """
        output_dir = Path(output_dir) if output_dir else self._output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}
        total = len(chapters)

        for idx, ch in enumerate(chapters, 1):
            ch_num = ch.get("num", str(idx))
            ch_title = ch.get("title", f"Chapter {ch_num}")
            ch_content = ch.get("content", "")

            if on_progress:
                on_progress(idx, total, f"Generating video: {ch_title}")

            result = self.generate_chapter_video(
                chapter_text=ch_content,
                chapter_num=ch_num,
                chapter_title=ch_title,
                output_dir=output_dir,
            )

            if result:
                results[ch_num] = result

            # Rate limiting
            time.sleep(1)

        console.print(f"[green]Generated {len(results)}/{total} chapter videos[/green]")
        return results
