"""
StudyCraft -- Video Generator.

Three-tier video generation strategy:

  1. OpenRouter video API (free models, async) — AI-generated visuals
  2. Manim animated scenes — programmatic animations: code write-on,
     flowcharts building, concept diagrams, bullet reveals with motion
  3. Pillow slideshow + ffmpeg — static slides, always available offline

Each tier falls through to the next on failure.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import textwrap
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

# ── Chapter content analysis ──────────────────────────────────────────────────

_CODE_RE = re.compile(r"```[\w]*\n(.*?)```", re.DOTALL)
_BULLET_RE = re.compile(r"^[-*•]\s+(.+)$", re.MULTILINE)
_NUMBERED_RE = re.compile(r"^\d+\.\s+(.+)$", re.MULTILINE)
_SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def _detect_chapter_type(text: str) -> str:
    """Classify chapter content to pick the best animation style."""
    code_blocks = _CODE_RE.findall(text)
    has_code = len(code_blocks) > 0
    has_math = bool(re.search(r"\$[^$]+\$|\\frac|\\sum|\\int", text))
    has_steps = len(_NUMBERED_RE.findall(text)) >= 3
    has_flow = bool(
        re.search(r"\b(flow|diagram|process|pipeline|architecture|sequence|step)\b", text, re.I)
    )

    if has_code:
        return "code"
    if has_math:
        return "math"
    if has_flow or has_steps:
        return "flow"
    return "concepts"


def _extract_key_points(text: str, max_points: int = 6) -> list[str]:
    bullets = _BULLET_RE.findall(text)
    numbered = _NUMBERED_RE.findall(text)
    points = (bullets + numbered)[:max_points]
    return [p[:80] for p in points] if points else ["See chapter content"]


def _extract_code_sample(text: str) -> str:
    """Extract the first meaningful code block."""
    blocks = _CODE_RE.findall(text)
    for block in blocks:
        lines = [line for line in block.strip().splitlines() if line.strip()]
        if lines:
            return "\n".join(lines[:12])
    return ""


def _extract_sections(text: str) -> list[tuple[str, list[str]]]:
    """Return [(section_title, [bullets])] from ## headings."""
    parts = re.split(r"^##\s+", text, flags=re.MULTILINE)
    result = []
    for part in parts[1:]:
        lines = part.strip().splitlines()
        title = lines[0].strip() if lines else "Section"
        bullets = []
        for line in lines[1:]:
            line = line.strip()
            if re.match(r"^[-*•]\s+", line):
                bullets.append(re.sub(r"^[-*•]\s+", "", line)[:70])
            elif re.match(r"^\d+\.\s+", line):
                bullets.append(re.sub(r"^\d+\.\s+", "", line)[:70])
            if len(bullets) >= 4:
                break
        if bullets:
            result.append((title, bullets))
    return result[:5]


# ── Manim scene generation ────────────────────────────────────────────────────


def _manim_available() -> bool:
    try:
        import manim  # noqa: F401

        return True
    except ImportError:
        return False


def _build_manim_scene(
    chapter_title: str,
    chapter_text: str,
    chapter_type: str,
) -> str:
    """Generate a Manim Python scene script for the chapter."""
    safe_title = re.sub(r"[^\w\s]", "", chapter_title)[:50]
    key_points = _extract_key_points(chapter_text)
    sections = _extract_sections(chapter_text)
    code_sample = _extract_code_sample(chapter_text)

    # Escape strings for Python source
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    title_esc = esc(safe_title)
    points_repr = repr([esc(p) for p in key_points])
    sections_repr = repr([(esc(t), [esc(b) for b in bs]) for t, bs in sections])

    if chapter_type == "code" and code_sample:
        code_esc = esc(code_sample)
        scene_body = f'''
        # Title
        title = Text("{title_esc}", font_size=40, color=BLUE_B)
        title.to_edge(UP)
        self.play(Write(title), run_time=1.5)
        self.wait(0.5)

        # Code block write-on
        code_str = """{code_esc}"""
        code = Code(
            code=code_str,
            tab_width=4,
            background="window",
            language="Java",
            font_size=18,
        )
        code.move_to(ORIGIN)
        self.play(FadeIn(code, shift=UP), run_time=2)
        self.wait(2)
        self.play(FadeOut(code))

        # Key points
        points = {points_repr}
        for i, pt in enumerate(points[:4]):
            bullet = Text(f"• {{pt}}", font_size=24, color=WHITE)
            bullet.move_to(UP * (1.5 - i * 0.8))
            self.play(FadeIn(bullet, shift=RIGHT * 0.3), run_time=0.6)
        self.wait(2)
'''
    elif chapter_type == "flow":
        scene_body = f'''
        # Title
        title = Text("{title_esc}", font_size=40, color=BLUE_B)
        title.to_edge(UP)
        self.play(Write(title), run_time=1.5)
        self.wait(0.5)

        # Animated flowchart from sections
        sections = {sections_repr}
        boxes = []
        arrows = []
        for i, (sec_title, _) in enumerate(sections[:4]):
            box = RoundedRectangle(corner_radius=0.2, width=4, height=0.8, color=BLUE_D)
            label = Text(sec_title[:35], font_size=20, color=WHITE)
            label.move_to(box)
            group = VGroup(box, label)
            group.move_to(UP * (2 - i * 1.4))
            boxes.append(group)

        for i, box in enumerate(boxes):
            self.play(FadeIn(box, shift=LEFT * 0.2), run_time=0.5)
            if i > 0:
                arr = Arrow(
                    boxes[i - 1].get_bottom(),
                    boxes[i].get_top(),
                    buff=0.1,
                    color=YELLOW,
                )
                self.play(GrowArrow(arr), run_time=0.4)
        self.wait(2)

        # Key points
        self.play(*[FadeOut(b) for b in boxes])
        points = {points_repr}
        for i, pt in enumerate(points[:5]):
            bullet = Text(f"• {{pt}}", font_size=22, color=WHITE)
            bullet.move_to(UP * (1.8 - i * 0.75))
            self.play(FadeIn(bullet, shift=RIGHT * 0.2), run_time=0.5)
        self.wait(2)
'''
    else:
        # concepts / math — animated bullet reveal with highlight boxes
        scene_body = f'''
        # Title card
        title = Text("{title_esc}", font_size=44, color=BLUE_B)
        subtitle = Text("Study Guide", font_size=24, color=GRAY)
        subtitle.next_to(title, DOWN, buff=0.3)
        self.play(Write(title), FadeIn(subtitle, shift=DOWN * 0.2), run_time=1.5)
        self.wait(1)
        self.play(FadeOut(title), FadeOut(subtitle))

        # Animated concept cards
        sections = {sections_repr}
        for sec_title, bullets in sections[:3]:
            header = Text(sec_title[:40], font_size=32, color=YELLOW)
            header.to_edge(UP, buff=0.5)
            self.play(Write(header), run_time=0.8)

            for i, bullet in enumerate(bullets[:4]):
                box = RoundedRectangle(corner_radius=0.15, width=9, height=0.65, color=BLUE_E)
                box.set_fill(BLUE_E, opacity=0.3)
                txt = Text(f"• {{bullet}}", font_size=22, color=WHITE)
                txt.move_to(box)
                grp = VGroup(box, txt)
                grp.move_to(UP * (1.5 - i * 0.9))
                self.play(FadeIn(grp, shift=RIGHT * 0.3), run_time=0.5)

            self.wait(1.5)
            self.play(FadeOut(header), *[FadeOut(m) for m in self.mobjects if m != header])

        # Summary
        summary = Text("End of: {title_esc}", font_size=30, color=GREEN_B)
        self.play(Write(summary), run_time=1)
        self.wait(1.5)
'''

    return textwrap.dedent(f"""\
from manim import *

class ChapterScene(Scene):
    def construct(self):
        self.camera.background_color = "#0f1117"
{textwrap.indent(textwrap.dedent(scene_body), '        ')}
""")


def _render_manim_scene(scene_script: str, output_path: Path) -> Path | None:
    """Write scene to temp file, render with Manim, return mp4 path."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        scene_file = tmp_path / "scene.py"
        scene_file.write_text(scene_script, encoding="utf-8")

        media_dir = tmp_path / "media"
        cmd = [
            "python",
            "-m",
            "manim",
            "render",
            "--quality",
            "m",  # 720p 30fps
            "--output_file",
            "output",
            "--media_dir",
            str(media_dir),
            "--disable_caching",
            str(scene_file),
            "ChapterScene",
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0:
            console.print(f"[yellow]Manim render error: {result.stderr.decode()[-300:]}[/yellow]")
            return None

        # Find the rendered mp4
        mp4_files = list(media_dir.rglob("*.mp4"))
        if not mp4_files:
            return None

        rendered = mp4_files[0]

        # Mux audio if output_path has a companion .mp3
        audio_path = output_path.with_suffix(".mp3")
        if audio_path.exists():
            muxed = tmp_path / "muxed.mp4"
            mux = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(rendered),
                    "-i",
                    str(audio_path),
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(muxed),
                ],
                capture_output=True,
            )
            if mux.returncode == 0:
                rendered = muxed

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(rendered.read_bytes())
        return output_path


# ── Slideshow fallback ────────────────────────────────────────────────────────


def _ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _render_slide(title: str, bullets: list[str], w: int, h: int):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (w, h), color=(15, 17, 35))
    draw = ImageDraw.Draw(img)

    for y in range(80):
        draw.line([(0, y), (w, y)], fill=(30, 50, 120))

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
        body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except OSError:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

    clean_title = re.sub(r"[^\x00-\x7F]", "", title)[:60]
    draw.text((60, 18), clean_title, font=title_font, fill=(109, 159, 255))
    draw.line([(60, 90), (w - 60, 90)], fill=(50, 70, 150), width=2)

    y = 130
    for bullet in bullets[:6]:
        clean = re.sub(r"[^\x00-\x7F]", "", bullet)
        draw.text((80, y), f"• {clean}", font=body_font, fill=(220, 230, 240))
        y += 70

    draw.text((60, h - 40), "StudyCraft", font=body_font, fill=(80, 100, 160))
    return img


def _generate_slideshow(
    chapter_text: str,
    chapter_title: str,
    output_path: Path,
    audio_path: Path | None = None,
) -> Path | None:
    try:
        from PIL import Image, ImageDraw, ImageFont  # noqa: F401
    except ImportError:
        console.print("[yellow]Pillow not installed — skipping slideshow[/yellow]")
        return None

    if not _ffmpeg_available():
        console.print("[yellow]ffmpeg not found — skipping slideshow[/yellow]")
        return None

    W, H, FPS, SLIDE_DURATION = 1280, 720, 24, 4
    slides: list[tuple[str, list[str]]] = [(chapter_title, ["Study Guide"])]
    for sec_title, bullets in _extract_sections(chapter_text):
        slides.append((sec_title, bullets))
    slides.append(("Summary", [f"End of: {chapter_title}"]))

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        frame_list = tmp_path / "frames.txt"
        lines = []
        for i, (title, bullets) in enumerate(slides):
            img = _render_slide(title, bullets, W, H)
            slide_path = tmp_path / f"slide_{i:04d}.png"
            img.save(str(slide_path))
            lines.append(f"file '{slide_path}'\nduration {SLIDE_DURATION}\n")
        last_slide = tmp_path / f"slide_{len(slides) - 1:04d}.png"
        lines.append(f"file '{last_slide}'")
        frame_list.write_text("".join(lines))

        silent_path = tmp_path / "silent.mp4"
        r = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(frame_list),
                "-vf",
                f"scale={W}:{H},fps={FPS}",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(silent_path),
            ],
            capture_output=True,
        )
        if r.returncode != 0:
            return None

        output_path.parent.mkdir(parents=True, exist_ok=True)
        if audio_path and audio_path.exists():
            r2 = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(silent_path),
                    "-i",
                    str(audio_path),
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(output_path),
                ],
                capture_output=True,
            )
            if r2.returncode != 0:
                output_path.write_bytes(silent_path.read_bytes())
        else:
            output_path.write_bytes(silent_path.read_bytes())

    console.print(f"[green]Slideshow saved:[/green] {output_path}")
    return output_path


# ── OpenRouter API ────────────────────────────────────────────────────────────


class VideoGenerator:
    """
    Generates video from chapter text using three strategies in order:
      1. OpenRouter video API (free models, async)
      2. Manim animated scenes (offline, programmatic animations)
      3. Pillow slideshow + ffmpeg (offline, always available)
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
        self._model = self._resolve_model(model)

    def _resolve_model(self, requested: str | None) -> str | None:
        if not self._api_key:
            return None
        try:
            if requested:
                info = get_model(requested)
                if info and info.get("is_free", False):
                    return requested
                console.print(
                    f"[yellow]⚠ '{requested}' is not free, auto-selecting free model[/yellow]"
                )
            free = get_free_models()
            if free:
                chosen = free[0]["id"]
                console.print(f"[dim]Video model: {chosen}[/dim]")
                return chosen
        except Exception:
            pass
        return None

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
                console.print(f"[dim]Video job: {status}[/dim]")
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
        return None

    def _generate_via_api(
        self, prompt: str, output_path: Path, chapter_num: str | None = None
    ) -> Path | None:
        if not self._api_key or not self._model:
            return None
        label = f"Chapter {chapter_num}" if chapter_num else "Video"
        console.print(f"[cyan]Generating video (API): {label} ({self._model})[/cyan]")
        try:
            resp = self._make_request(
                "POST",
                "",
                {
                    "model": self._model,
                    "prompt": prompt[:500],
                    "duration": 5,
                    "resolution": "720p",
                    "aspect_ratio": "16:9",
                    "generate_audio": False,
                },
            )
            job_id = resp.get("id")
            if not job_id:
                return None
            video_url = self._poll_job(job_id, resp.get("polling_url"))
            if not video_url:
                return None
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with urlopen(Request(video_url), timeout=60) as r:
                output_path.write_bytes(r.read())
            console.print(f"[green]API video saved:[/green] {output_path}")
            return output_path
        except Exception as exc:
            console.print(f"[yellow]API video failed ({exc}) — trying Manim[/yellow]")
            return None

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

        # Tier 1: OpenRouter API
        if self._model and self._api_key:
            words = chapter_text.split()[:50]
            prompt = f"Educational animated video about {chapter_title}. {' '.join(words)}"
            result = self._generate_via_api(prompt, output_path, chapter_num)
            if result:
                return result

        # Tier 2: Manim animated scene
        if _manim_available():
            console.print(f"[cyan]Generating Manim animation: Chapter {chapter_num}[/cyan]")
            chapter_type = _detect_chapter_type(chapter_text)
            scene_script = _build_manim_scene(chapter_title, chapter_text, chapter_type)
            # Pass audio path via companion file convention
            if audio_path and audio_path.exists():
                # _render_manim_scene checks for .mp3 sibling of output_path
                companion = output_path.with_suffix(".mp3")
                companion.write_bytes(audio_path.read_bytes())
            result = _render_manim_scene(scene_script, output_path)
            if result:
                console.print(f"[green]Manim video saved:[/green] {result}")
                return result
            console.print("[yellow]Manim failed — falling back to slideshow[/yellow]")
        else:
            console.print("[dim]Manim not installed — using slideshow[/dim]")

        # Tier 3: Pillow slideshow
        return _generate_slideshow(chapter_text, chapter_title, output_path, audio_path)

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
