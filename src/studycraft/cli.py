"""
StudyCraft CLI

Commands:
  studycraft generate <file>          — Generate a full practice guide
  studycraft generate <file> -c 3    — Generate chapter 3 only
  studycraft generate <file> -r 5    — Resume from chapter 5
  studycraft export <guide.md>       — Re-export existing guide to HTML/PDF
  studycraft inspect <file>          — Show detected chapter outline only
  studycraft models                  — List recommended OpenRouter models
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

# Silence pkg_resources deprecation from chatterbox-tts dependency (perth)
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)
warnings.filterwarnings("ignore", message="Deprecated call to", category=UserWarning)

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()

app = typer.Typer(
    name="studycraft",
    help="📖 StudyCraft — craft structured practice guides from any document",
    rich_markup_mode="rich",
    invoke_without_command=True,
)
console = Console()


@app.callback()
def _default(ctx: typer.Context) -> None:
    """Launch the web UI if no command is given."""
    if ctx.invoked_subcommand is None:
        from .web import main as web_main

        web_main()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _api_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY") or os.getenv("STUDYCRAFT_API_KEY")
    if not key:
        console.print(
            Panel(
                "[red]No API key found.[/red]\n\n"
                "Set [cyan]OPENROUTER_API_KEY[/cyan] in your [cyan].env[/cyan] file:\n\n"
                "  [dim]OPENROUTER_API_KEY=your_key_here[/dim]\n\n"
                "Get a free key at [link]https://openrouter.ai[/link]",
                title="⚠ Missing API Key",
                border_style="red",
            )
        )
        raise typer.Exit(1)
    return key


def _validate_file(path: Path) -> None:
    from .loader import SUPPORTED

    if not path.exists():
        console.print(f"[red]✗ File not found:[/red] {path}")
        raise typer.Exit(1)
    if path.suffix.lower() not in SUPPORTED:
        from .loader import supported_extensions

        console.print(
            f"[red]✗ Unsupported file type:[/red] '{path.suffix}'\n"
            f"  Supported: {', '.join(supported_extensions())}"
        )
        raise typer.Exit(1)


# ── Commands ──────────────────────────────────────────────────────────────────


@app.command()
def generate(
    document: str = typer.Argument(
        ..., help="Path to the document (PDF, DOCX, TXT, MD, RTF, EPUB)"
    ),
    output: str = typer.Option("output", "--output", "-o", help="Output directory"),
    model: str = typer.Option(
        "openrouter/free",
        "--model",
        "-m",
        help="OpenRouter model ID",
    ),
    subject: str | None = typer.Option(
        None,
        "--subject",
        "-s",
        help="Override the auto-detected subject name",
    ),
    chapter: int | None = typer.Option(
        None,
        "--chapter",
        "-c",
        help="Generate only this chapter number",
    ),
    resume_from: int = typer.Option(
        1,
        "--resume-from",
        "-r",
        help="Resume from this chapter number (uses cache for earlier chapters)",
    ),
    rate_limit: int = typer.Option(
        5,
        "--rate-limit",
        help="Seconds to pause between chapters (free-tier rate limiting)",
    ),
    with_answers: bool = typer.Option(
        False,
        "--with-answers",
        help="Generate an answer key after the guide",
    ),
    context: list[str] | None = typer.Option(
        None,
        "--context",
        "-x",
        help="Extra files to index into RAG for richer context (not generated)",
    ),
    workers: int = typer.Option(
        1,
        "--workers",
        "-w",
        help="Number of parallel workers for chapter generation",
    ),
    clear_cache: bool = typer.Option(
        False,
        "--clear-cache",
        help="Delete cached chapters before running",
    ),
    theme: str | None = typer.Option(
        None,
        "--theme",
        "-t",
        help="Export theme (dark, light, nord, solarized, dracula, github, monokai, ocean, rose-pine)",
    ),
    difficulty: str = typer.Option(
        "intermediate",
        "--difficulty",
        "-d",
        help="Difficulty level (beginner, intermediate, advanced)",
    ),
    with_audio: bool = typer.Option(
        False,
        "--with-audio",
        help="Generate audio guide using TTS",
    ),
    tts_engine: str = typer.Option(
        "kitten",
        "--tts-engine",
        help="TTS engine: kitten, chatterbox, coqui, openrouter",
    ),
    tts_voice: str | None = typer.Option(
        None,
        "--tts-voice",
        help="Voice name (engine-specific: Bella/Jasper for kitten, etc.)",
    ),
    tts_speed: float = typer.Option(
        1.0,
        "--tts-speed",
        help="Playback speed multiplier (0.5-2.0)",
    ),
    with_video: bool = typer.Option(
        False,
        "--with-video",
        help="Generate video guide using OpenRouter (free models only)",
    ),
    video_model: str = typer.Option(
        "google/veo-3.1",
        "--video-model",
        help="Video generation model (must be free)",
    ),
    video_resolution: str = typer.Option(
        "720p",
        "--video-resolution",
        help="Video resolution: 720p or 1080p",
    ),
) -> None:
    """[bold]Generate[/bold] a full practice guide from any document."""
    doc_path = Path(document)
    _validate_file(doc_path)

    api_key = _api_key()

    console.print(
        Panel(
            f"[bold]Document:[/bold] {doc_path.name}\n"
            f"[bold]Model:[/bold]    {model}\n"
            f"[bold]Theme:[/bold]    {theme or 'dark'}\n"
            f"[bold]Output:[/bold]   {output}/",
            title="🔨 StudyCraft — Generating Guide",
            border_style="cyan",
        )
    )

    if clear_cache:
        import shutil

        cache = Path(output) / ".cache"
        if cache.exists():
            shutil.rmtree(cache)
            console.print("[dim]🗑 Cache cleared[/dim]")

    from .engine import StudyCraft

    craft = StudyCraft(
        api_key=api_key,
        model=model,
        output_dir=output,
        rate_limit_seconds=rate_limit,
    )

    try:
        paths = craft.run(
            document_path=doc_path,
            subject=subject,
            resume_from=resume_from,
            only_chapter=chapter,
            with_answers=with_answers,
            context_files=context,
            workers=workers,
            theme=theme,
            difficulty=difficulty,
            with_audio=with_audio,
            tts_engine=tts_engine,
            tts_voice=tts_voice,
            tts_speed=tts_speed,
            with_video=with_video,
            video_model=video_model,
            video_resolution=video_resolution,
        )
    except ValueError as exc:
        console.print(f"[red]✗ Error:[/red] {exc}")
        raise typer.Exit(1)

    console.print("\n[bold green]🎉 Guide ready![/bold green]")
    for fmt, path in paths.items():
        console.print(f"  [cyan]{fmt.upper()}[/cyan] → {path.resolve()}")


@app.command()
def inspect(
    document: str = typer.Argument(..., help="Path to the document"),
    rag: bool = typer.Option(
        False,
        "--rag",
        help="Also index into RAG and show which chunks match each chapter",
    ),
) -> None:
    """[bold]Inspect[/bold] a document — show detected chapters without generating."""
    doc_path = Path(document)
    _validate_file(doc_path)

    from .detector import detect_chapters
    from .loader import load_document

    console.print(f"[cyan]📄 Loading:[/cyan] {doc_path.name}")
    text = load_document(doc_path)

    console.print("[cyan]🔍 Detecting chapters…[/cyan]")
    chapters = detect_chapters(text)

    table = Table(title=f"Chapter Outline — {doc_path.name}", show_lines=True)
    table.add_column("#", style="bold cyan", width=6)
    table.add_column("Title", style="white")
    table.add_column("Subchapters", style="dim")

    for ch in chapters:
        subs = ", ".join(s["num"] for s in ch["subchapters"]) or "—"
        table.add_row(ch["num"], ch["title"], subs)

    console.print(table)
    console.print(f"\n[green]Total:[/green] {len(chapters)} chapters")

    if rag:
        from .rag import RAGIndex

        console.print("\n[cyan]Indexing into RAG…[/cyan]")
        idx = RAGIndex()
        idx.clear()
        idx.index(text, source_name=doc_path.stem)
        console.print(f"[green]Total chunks:[/green] {idx.chunk_count()}\n")

        for ch in chapters:
            sub_titles = " ".join(s["title"] for s in ch["subchapters"])
            query = f"{ch['title']} {sub_titles}"
            hits = idx.query_detailed(query, n_results=3)
            console.print(f"[bold]Ch {ch['num']}: {ch['title']}[/bold]")
            if not hits:
                console.print("  [dim]No matching chunks[/dim]")
            for h in hits:
                console.print(
                    f"  [dim]chunk {h['chunk_index']} from {h['source']} "
                    f"(dist={h['distance']}):[/dim] {h['text'][:120]}"
                )
            console.print()


@app.command()
def export(
    markdown_file: str = typer.Argument(..., help="Path to an existing .md guide"),
    output: str = typer.Option("output", "--output", "-o"),
    name: str = typer.Option("StudyCraft_Practice_Guide", "--name", "-n", help="Base filename"),
    theme: str | None = typer.Option(
        None,
        "--theme",
        "-t",
        help="Export theme (dark, light, nord, solarized, dracula, github, monokai, ocean, rose-pine)",
    ),
    difficulty: str = typer.Option(
        "intermediate",
        "--difficulty",
        "-d",
        help="Difficulty level (beginner, intermediate, advanced)",
    ),
) -> None:
    """[bold]Re-export[/bold] an existing Markdown guide to HTML, PDF, DOCX, EPUB."""
    md_path = Path(markdown_file)
    if not md_path.exists():
        console.print(f"[red]✗ File not found:[/red] {md_path}")
        raise typer.Exit(1)

    from .export import export_all

    text = md_path.read_text(encoding="utf-8")
    paths = export_all(text, Path(output), base_name=name, theme=theme)
    console.print("[green]✓ Re-export complete.[/green]")
    for fmt, path in paths.items():
        console.print(f"  [cyan]{fmt.upper()}[/cyan] → {path.resolve()}")


@app.command()
def generate_audio(
    markdown_file: str = typer.Argument(..., help="Path to an existing .md guide"),
    output: str = typer.Option(
        "output/audio", "--output", "-o", help="Output directory for audio files"
    ),
    tts_engine: str = typer.Option(
        "kitten",
        "--tts-engine",
        help="TTS engine: kitten, chatterbox, coqui, openrouter",
    ),
    tts_voice: str | None = typer.Option(
        None,
        "--tts-voice",
        help="Voice name (engine-specific: Bella/Jasper for kitten, etc.)",
    ),
    tts_speed: float = typer.Option(
        1.0,
        "--tts-speed",
        help="Playback speed multiplier (0.5-2.0)",
    ),
) -> None:
    """[bold]Generate audio[/bold] from an existing Markdown guide."""
    md_path = Path(markdown_file)
    if not md_path.exists():
        console.print(f"[red]✗ File not found:[/red] {md_path}")
        raise typer.Exit(1)

    from .audio_generator import AudioGenerator

    console.print(f"[cyan]Loading:[/cyan] {md_path.name}")
    text = md_path.read_text(encoding="utf-8")

    # Parse chapters from markdown by headings
    import re

    console.print("[cyan]Extracting chapters...[/cyan]")
    chapters = []
    current_chapter = None
    current_content = []

    for line in text.split("\n"):
        heading_match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading_match:
            # Save previous chapter
            if current_chapter:
                current_chapter["content"] = "\n".join(current_content)
                chapters.append(current_chapter)
            num = heading_match.group(2)[:50]
            current_chapter = {
                "num": num,
                "title": num,
                "content": "",
            }
            current_content = []
        elif current_chapter:
            current_content.append(line)

    # Don't forget the last chapter
    if current_chapter:
        current_chapter["content"] = "\n".join(current_content)
        chapters.append(current_chapter)

    if not chapters:
        # Fallback: treat entire document as one chapter
        chapters = [{"num": "1", "title": md_path.stem, "content": text}]

    console.print(f"[green]Found {len(chapters)} chapters[/green]")

    console.print(f"[cyan]Initializing TTS engine:[/cyan] {tts_engine}")
    audio_gen = AudioGenerator(
        engine_name=tts_engine,
        voice=tts_voice,
        speed=tts_speed,
    )

    results = audio_gen.generate_all_chapters(
        chapters=chapters,
        output_dir=output,
    )

    console.print("\n[bold green]🎧 Audio guide ready![/bold green]")
    for ch_num, path in results.items():
        console.print(f"  [cyan]{ch_num}[/cyan] → {path.resolve()}")


@app.command()
def generate_video(
    markdown_file: str = typer.Argument(..., help="Path to an existing .md guide"),
    output: str = typer.Option(
        "output/videos", "--output", "-o", help="Output directory for video files"
    ),
    video_model: str = typer.Option(
        "google/veo-3.1",
        "--video-model",
        help="Video generation model (must be free)",
    ),
    video_resolution: str = typer.Option(
        "720p",
        "--video-resolution",
        help="Video resolution: 720p or 1080p",
    ),
) -> None:
    """[bold]Generate video[/bold] from an existing Markdown guide using OpenRouter."""
    md_path = Path(markdown_file)
    if not md_path.exists():
        console.print(f"[red]✗ File not found:[/red] {md_path}")
        raise typer.Exit(1)

    from .video_generator import VideoGenerator

    console.print(f"[cyan]Loading:[/cyan] {md_path.name}")
    text = md_path.read_text(encoding="utf-8")

    # Parse chapters from markdown by headings
    import re

    console.print("[cyan]Extracting chapters...[/cyan]")
    chapters = []
    current_chapter = None
    current_content = []

    for line in text.split("\n"):
        heading_match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading_match:
            # Save previous chapter
            if current_chapter:
                current_chapter["content"] = "\n".join(current_content)
                chapters.append(current_chapter)
            num = heading_match.group(2)[:50]
            current_chapter = {
                "num": num,
                "title": num,
                "content": "",
            }
            current_content = []
        elif current_chapter:
            current_content.append(line)

    # Don't forget the last chapter
    if current_chapter:
        current_chapter["content"] = "\n".join(current_content)
        chapters.append(current_chapter)

    if not chapters:
        # Fallback: treat entire document as one chapter
        chapters = [{"num": "1", "title": md_path.stem, "content": text}]

    console.print(f"[green]Found {len(chapters)} chapters[/green]")

    console.print(f"[cyan]Initializing Video Generator:[/cyan] {video_model}")
    video_gen = VideoGenerator(
        model=video_model,
        output_dir=output,
    )

    results = video_gen.generate_all_chapters(
        chapters=chapters,
        output_dir=output,
    )

    console.print("\n[bold green]🎥 Video guide ready![/bold green]")
    for ch_num, path in results.items():
        console.print(f"  [cyan]{ch_num}[/cyan] → {path.resolve()}")


@app.command()
def validate(
    markdown_file: str = typer.Argument(..., help="Path to a generated .md guide"),
) -> None:
    """[bold]Validate[/bold] a generated guide — check sections, examples, quiz, placeholders."""
    md_path = Path(markdown_file)
    if not md_path.exists():
        console.print(f"[red]✗ File not found:[/red] {md_path}")
        raise typer.Exit(1)

    from .validator import validate_guide

    text = md_path.read_text(encoding="utf-8")
    results = validate_guide(text)

    if not results:
        console.print("[yellow]No chapters found to validate.[/yellow]")
        raise typer.Exit(1)

    table = Table(title=f"Validation — {md_path.name}", show_lines=True)
    table.add_column("Chapter", style="cyan", max_width=50)
    table.add_column("Status", width=8)
    table.add_column("Details", style="dim")

    all_passed = True
    for r in results:
        status = "[green]✓[/green]" if r.passed else "[red]✗[/red]"
        if not r.passed:
            all_passed = False
        table.add_row(r.chapter_label[:50], status, r.summary())

    console.print(table)
    if all_passed:
        console.print("\n[bold green]All chapters passed validation.[/bold green]")
    else:
        console.print("\n[yellow]Some chapters have issues. Consider regenerating.[/yellow]")


@app.command()
def gist(
    markdown_file: str = typer.Argument(..., help="Path to a .md guide to publish"),
    public: bool = typer.Option(False, "--public", help="Make the gist public"),
) -> None:
    """[bold]Publish[/bold] a Markdown guide as a GitHub Gist."""
    import json
    import urllib.error
    import urllib.request

    md_path = Path(markdown_file)
    if not md_path.exists():
        console.print(f"[red]File not found:[/red] {md_path}")
        raise typer.Exit(1)

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        console.print(
            "[red]GITHUB_TOKEN not set.[/red] Add it to your .env file.\n"
            "  Create a token at https://github.com/settings/tokens (gist scope)"
        )
        raise typer.Exit(1)

    content = md_path.read_text(encoding="utf-8")
    payload = json.dumps(
        {
            "description": f"StudyCraft Practice Guide - {md_path.stem}",
            "public": public,
            "files": {md_path.name: {"content": content}},
        }
    ).encode()

    req = urllib.request.Request(
        "https://api.github.com/gists",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            console.print(f"[green]Gist created![/green] {data['html_url']}")
    except urllib.error.HTTPError as exc:
        console.print(f"[red]GitHub API error:[/red] {exc.code} {exc.reason}")
        raise typer.Exit(1)


@app.command()
def models(
    free: bool = typer.Option(False, "--free", help="Show only free models"),
    vision: bool = typer.Option(False, "--vision", help="Show only vision-capable models"),
    search: str | None = typer.Option(None, "--search", "-q", help="Search by name or ID"),
    refresh: bool = typer.Option(False, "--refresh", help="Force refresh from OpenRouter API"),
) -> None:
    """[bold]List[/bold] available OpenRouter models (fetched from API, cached 24h)."""
    from .model_registry import (
        fetch_models,
        get_free_models,
        get_vision_models,
        search_models,
    )

    if refresh:
        fetch_models(force=True)

    if search:
        result = search_models(search)
    elif free and vision:
        result = get_free_models(vision_only=True)
    elif free:
        result = get_free_models()
    elif vision:
        result = get_vision_models()
    else:
        result = fetch_models()

    if not result:
        console.print("[yellow]No models found. Try --refresh or check your connection.[/yellow]")
        raise typer.Exit(1)

    # Show top 30 to keep output manageable
    shown = result[:30]
    title = "OpenRouter Models"
    if free:
        title += " (Free)"
    if vision:
        title += " (Vision)"
    if search:
        title += f" matching '{search}'"

    table = Table(title=title, show_lines=True)
    table.add_column("Model ID", style="cyan", max_width=45)
    table.add_column("Context", style="dim", width=8)
    table.add_column("Vision", width=6)
    table.add_column("Cost", width=8)

    for m in shown:
        ctx = f"{m['context_length'] // 1000}k" if m["context_length"] else "?"
        vis = "[green]Yes[/green]" if m["has_vision"] else "[dim]No[/dim]"
        cost = "[green]Free[/green]" if m["is_free"] else "Paid"
        table.add_row(m["id"], ctx, vis, cost)

    console.print(table)
    if len(result) > 30:
        console.print(
            f"\n[dim]Showing 30 of {len(result)} models. Use --search to narrow down.[/dim]"
        )
    console.print(
        "\n[dim]Use with:[/dim] [cyan]studycraft generate doc.pdf --model <model-id>[/cyan]"
        "\n[dim]Filters:[/dim] --free  --vision  --search <query>  --refresh"
    )


@app.command(name="setup-pdf")
def setup_pdf() -> None:
    """[bold]Install[/bold] Chromium browser for PDF export with emoji support."""
    import subprocess

    console.print("[cyan]Installing Chromium for PDF export...[/cyan]")
    result = subprocess.run(
        ["uv", "run", "playwright", "install", "chromium"],
        capture_output=False,
    )
    if result.returncode == 0:
        console.print("[green]\u2713 Chromium installed. PDF export is ready.[/green]")
    else:
        console.print(
            "[yellow]\u26a0 Could not install Chromium. PDF will use fpdf2 fallback.[/yellow]"
        )


def main() -> None:
    app()
