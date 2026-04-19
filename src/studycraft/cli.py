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
from pathlib import Path
from typing import Optional

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
    no_args_is_help=True,
)
console = Console()


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
        ..., help="Path to the document (PDF, DOCX, TXT, MD, RTF)"
    ),
    output: str = typer.Option("output", "--output", "-o", help="Output directory"),
    model: str = typer.Option(
        "openrouter/free",
        "--model",
        "-m",
        help="OpenRouter model ID",
    ),
    subject: Optional[str] = typer.Option(
        None,
        "--subject",
        "-s",
        help="Override the auto-detected subject name",
    ),
    chapter: Optional[int] = typer.Option(
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
    context: Optional[list[str]] = typer.Option(
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
) -> None:
    """[bold]Generate[/bold] a full practice guide from any document."""
    doc_path = Path(document)
    _validate_file(doc_path)

    api_key = _api_key()

    console.print(
        Panel(
            f"[bold]Document:[/bold] {doc_path.name}\n"
            f"[bold]Model:[/bold]    {model}\n"
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
        False, "--rag", help="Also index into RAG and show which chunks match each chapter"
    ),
) -> None:
    """[bold]Inspect[/bold] a document — show detected chapters without generating."""
    doc_path = Path(document)
    _validate_file(doc_path)

    from .loader import load_document
    from .detector import detect_chapters

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
    name: str = typer.Option(
        "StudyCraft_Practice_Guide", "--name", "-n", help="Base filename"
    ),
) -> None:
    """[bold]Re-export[/bold] an existing Markdown guide to HTML and PDF."""
    md_path = Path(markdown_file)
    if not md_path.exists():
        console.print(f"[red]✗ File not found:[/red] {md_path}")
        raise typer.Exit(1)

    from .export import export_all

    text = md_path.read_text(encoding="utf-8")
    paths = export_all(text, Path(output), base_name=name)
    console.print("[green]✓ Re-export complete.[/green]")
    for fmt, path in paths.items():
        console.print(f"  [cyan]{fmt.upper()}[/cyan] → {path.resolve()}")


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
def models() -> None:
    """[bold]List[/bold] recommended OpenRouter models for guide generation."""
    table = Table(title="Recommended OpenRouter Models", show_lines=True)
    table.add_column("Model ID", style="cyan")
    table.add_column("Quality", style="green")
    table.add_column("Speed", style="yellow")
    table.add_column("Cost")

    rows = [
        ("openrouter/free", "Good", "Fast", "Free"),
        ("mistralai/mistral-7b-instruct:free", "Good", "Fast", "Free"),
        ("meta-llama/llama-3.3-70b-instruct:free", "Very Good", "Medium", "Free"),
        ("google/gemma-3-27b-it:free", "Very Good", "Medium", "Free"),
        ("anthropic/claude-3-5-haiku", "Excellent", "Fast", "Paid"),
        ("anthropic/claude-sonnet-4-5", "Best", "Medium", "Paid"),
        ("openai/gpt-4o-mini", "Very Good", "Fast", "Paid"),
    ]
    for row in rows:
        table.add_row(*row)

    console.print(table)
    console.print(
        "\n[dim]Use with:[/dim] [cyan]studycraft generate doc.pdf --model <model-id>[/cyan]"
    )


def main() -> None:
    app()
