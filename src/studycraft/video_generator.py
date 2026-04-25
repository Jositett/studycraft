"""
StudyCraft -- Video Generator.

Generates video content from chapter text using:
  1. OpenRouter video generation API (free models only, async)
  2. Slideshow fallback — Pillow-rendered slides + TTS audio via ffmpeg
     (works offline, no API required, always available)
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from rich.console import Console

from .model_registry import get_free_models, get_model

console = Console()

_VIDEO_API_BASE = "https://openrouter.ai/api/v1/videos"
_POLL_INTERVAL = 30
_TIMEOUT = 600


class VideoGenerator:
    """
    Generates video from chapter text.

    Strategy (in order):
      1. OpenRouter video API (free models only) — if api_key + free model available
      2. Slideshow — Pillow slides + ffmpeg composition (offline fallback, always tried)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = _VIDEO_API_BASE,
        output_dir: str | Path = "output/videos",
    ) -> None:
        from os import getenv

        self._api_key = api_key or getenv("OPENROUTER_API_KEY") or getenv("STUDYCRAFT_API_KEY")
        self._base_url = base_url
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Resolve model: use provided, or auto-select first free model
        self._model = self._resolve_model(model)

    def _resolve_model(self, requested: str | None) -> str | None:
        """Return a verified free model ID, or None if none available."""
        if not self._api_key:
            return None
        try:
            if requested:
                info = get_model(requested)
                if info and info.get("is_free", False):
                    return requested
                # Requested model is paid or unknown — fall through to auto-select
                console.print(
                    f"[yellow]⚠ Model '{requested}' is not free, auto-selecting free model[/yellow]"
                )
            free = get_free_models()
            if free:
                chosen = free[0]["id"]
                console.print(f"[dim]Video model: {chosen}[/dim]")
                return chosen
        except Exception:
            pass
        return None

    # ── OpenRouter API ────────────────────────────────────────────────────────

    def _make_request(self, method: str, endpoint: str, data: dict | None = None) -> dict:
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

    def _generate_via_api(
        self,
        prompt: str,
        output_path: Path,
        chapter_num: str | None = None,
    ) -> Path | None:
        """Submit to OpenRouter video API and download result."""
        if not self._api_key or not self._model:
            return None

        label = f"Chapter {chapter_num}" if chapter_num else "Video"
        console.print(f"[cyan]Generating video (API): {label} ({self._model})[/cyan]")

        try:
            response = self._make_request("POST", "", {
                "model": self._model,
                "prompt": prompt[:500],
                "duration": 5,
                "resolution": "720p",
                "aspect_ratio": "16:9",
                "generate_audio": False,
            })
            job_id = response.get("id")
            polling_url = response.get("polling_url")
            if not job_id:
                return None

            video_url = self._poll_job(job_id, polling_url)
            if not video_url:
                return None

            output_path.parent.mkdir(parents=True, exist_ok=True)
            req = Request(video_url)
            with urlopen(req, timeout=60) as resp:
                output_path.write_bytes(resp.read())
            console.print(f"[green]Video saved:[/green] {output_path}")
            return output_path

        except Exception as exc:
            console.print(f"[yellow]API video failed: {exc} — falling back to slideshow[/yellow]")
            return None

    def _poll_job(self, job_id: str, polling_url: str | None = None) -> str | None:
        start = time.time()
        while time.time() - start < _TIMEOUT:
            try:
                if polling_url:
                    req = Request(
                        polling_url,
                        headers={"Authorization": f"Bearer {self._api_key}"},
                    )
                    with urlopen(req, timeout=30) as resp:
                        data = json.loads(resp.read())
                else:
                    data = self._make_request("GET", f"/{job_id}")

                status = data.get("status", "unknown")
                console.print(f"[dim]Video job status: {status}[/dim]")

                if status == "completed":
                    urls = data.get("unsigned_urls", [])
                    return urls[0] if urls else None
                if status in ("failed", "cancelled", "expired"):
                    console.print(f"[red]Video job {status}: {data.get('error', '')}[/red]")
                    return None

                time.sleep(_POLL_INTERVAL)
            except Exception as exc:
                console.print(f"[yellow]Polling error: {exc}[/yellow]")
                time.sleep(_POLL_INTERVAL)

        console.print("[red]Video generation timed out[/red]")
        return None

    # ── Slideshow fallback ────────────────────────────────────────────────────

    def _generate_slideshow(
        self,
        chapter_text: str,
        chapter_title: str,
        output_path: Path,
        audio_path: Path | None = None,
        chapter_num: str | None = None,
    ) -> Path | None:
        """
        Build a slideshow video from chapter content using Pillow + ffmpeg.

        Slides:
          - Title slide
          - One slide per key point / bullet extracted from the chapter
          - Summary slide
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            console.print("[yellow]Pillow not installed — skipping slideshow[/yellow]")
            return None

        if not _ffmpeg_available():
            console.print("[yellow]ffmpeg not found — skipping slideshow[/yellow]")
            return None

        label = f"Chapter {chapter_num}" if chapter_num else chapter_title
        console.print(f"[cyan]Generating slideshow: {label}[/cyan]")

        slides = _extract_slides(chapter_text, chapter_title)
        W, H, FPS, SLIDE_DURATION = 1280, 720, 24, 4

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            frame_list = tmp_path / "frames.txt"
            lines = []

            for i, (title, bullets) in enumerate(slides):
                img = _render_slide(title, bullets, W, H)
                slide_path = tmp_path / f"slide_{i:04d}.png"
                img.save(str(slide_path))
                lines.append(f"file '{slide_path}'\nduration {SLIDE_DURATION}\n")

            # ffmpeg concat requires last entry repeated
            lines.append(f"file '{tmp_path / f\"slide_{len(slides)-1:04d}.png\"}'")
            frame_list.write_text("".join(lines))

            output_path.parent.mkdir(parents=True, exist_ok=True)
            silent_path = tmp_path / "silent.mp4"

            # Build silent video from slides
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(frame_list),
                "-vf", f"scale={W}:{H},fps={FPS}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(silent_path),
            ]
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                console.print(f"[red]ffmpeg slide error: {result.stderr.decode()[:200]}[/red]")
                return None

            # Mux audio if provided
            if audio_path and audio_path.exists():
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(silent_path),
                    "-i", str(audio_path),
                    "-c:v", "copy", "-c:a", "aac",
                    "-shortest", str(output_path),
                ]
            else:
                cmd = [
                    "ffmpeg", "-y", "-i", str(silent_path),
                    "-c", "copy", str(output_path),
                ]

            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                console.print(f"[red]ffmpeg mux error: {result.stderr.decode()[:200]}[/red]")
                return None

        console.print(f"[green]Slideshow saved:[/green] {output_path}")
        return output_path

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_chapter_video(
        self,
        chapter_text: str,
        chapter_num: str,
        chapter_title: str,
        output_dir: str | Path | None = None,
        audio_path: Path | None = None,
    ) -> Path | None:
        output_dir = Path(output_dir) if output_dir else self._output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        safe = re.sub(r"[^\w\s-]", "", chapter_title).strip().replace(" ", "_")[:50]
        output_path = output_dir / f"ch{chapter_num.replace('.', '_')}_{safe}.mp4"

        # Try OpenRouter API first
        if self._model and self._api_key:
            words = chapter_text.split()[:50]
            prompt = f"Educational video about {chapter_title}. Key concepts: {' '.join(words)}"
            result = self._generate_via_api(prompt, output_path, chapter_num)
            if result:
                return result

        # Slideshow fallback
        return self._generate_slideshow(
            chapter_text, chapter_title, output_path,
            audio_path=audio_path, chapter_num=chapter_num,
        )

    def generate_all_chapters(
        self,
        chapters: list[dict],
        output_dir: str | Path | None = None,
        audio_paths: dict[str, Path] | None = None,
        on_progress=None,
    ) -> dict[str, Path]:
        output_dir = Path(output_dir) if output_dir else self._output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}
        total = len(chapters)

        for idx, ch in enumerate(chapters, 1):
            ch_num = ch.get("num", str(idx))
            ch_title = ch.get("title", f"Chapter {ch_num}")
            ch_content = ch.get("content", "")
            audio = audio_paths.get(ch_num) if audio_paths else None

            if on_progress:
                on_progress(idx, total, f"Generating video: {ch_title}")

            result = self.generate_chapter_video(
                chapter_text=ch_content,
                chapter_num=ch_num,
                chapter_title=ch_title,
                output_dir=output_dir,
                audio_path=audio,
            )
            if result:
                results[ch_num] = result

            time.sleep(0.5)

        console.print(f"[green]Generated {len(results)}/{total} chapter videos[/green]")
        return results


# ── Helpers ───────────────────────────────────────────────────────────────────


def _ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _extract_slides(text: str, title: str) -> list[tuple[str, list[str]]]:
    """Extract (slide_title, [bullet, ...]) pairs from chapter markdown."""
    slides: list[tuple[str, list[str]]] = []

    # Title slide
    slides.append((title, ["Study Guide"]))

    # Extract ## sections as slides
    sections = re.split(r"^##\s+", text, flags=re.MULTILINE)
    for section in sections[1:]:  # skip preamble
        lines = section.strip().splitlines()
        if not lines:
            continue
        sec_title = lines[0].strip()
        bullets = []
        for line in lines[1:]:
            line = line.strip()
            # Grab bullet points and numbered items
            if re.match(r"^[-*•]\s+", line):
                bullets.append(re.sub(r"^[-*•]\s+", "", line)[:80])
            elif re.match(r"^\d+\.\s+", line):
                bullets.append(re.sub(r"^\d+\.\s+", "", line)[:80])
            if len(bullets) >= 5:
                break
        if bullets:
            slides.append((sec_title, bullets))

    # Summary slide
    slides.append(("Summary", [f"End of: {title}"]))
    return slides


def _render_slide(title: str, bullets: list[str], w: int, h: int):
    """Render a single slide as a PIL Image."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (w, h), color=(15, 17, 35))
    draw = ImageDraw.Draw(img)

    # Gradient-like header bar
    for y in range(80):
        alpha = int(255 * (1 - y / 80))
        draw.line([(0, y), (w, y)], fill=(30, 50, 120))

    # Try to load a font, fall back to default
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
        body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except (OSError, IOError):
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

    # Title
    clean_title = re.sub(r"[^\x00-\x7F]", "", title)[:60]
    draw.text((60, 20), clean_title, font=title_font, fill=(109, 159, 255))

    # Divider
    draw.line([(60, 90), (w - 60, 90)], fill=(50, 70, 150), width=2)

    # Bullets
    y = 130
    for bullet in bullets[:6]:
        clean = re.sub(r"[^\x00-\x7F]", "", bullet)
        draw.text((80, y), f"• {clean}", font=body_font, fill=(220, 230, 240))
        y += 70

    # Footer
    draw.text((60, h - 40), "StudyCraft", font=body_font, fill=(80, 100, 160))

    return img
