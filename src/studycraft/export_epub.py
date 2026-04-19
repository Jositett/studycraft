"""
StudyCraft -- EPUB export.

Converts Markdown guide text into an .epub file using ebooklib.
"""

from __future__ import annotations

import re
from pathlib import Path

import markdown as md_lib
from rich.console import Console

console = Console()

_EPUB_CSS = """
body { font-family: Georgia, serif; line-height: 1.6; color: #111; }
h1 { color: #2563eb; border-bottom: 2px solid #2563eb; padding-bottom: 4px; }
h2 { color: #1e3a8a; }
h3 { color: #7c3aed; }
pre { background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; }
code { font-family: monospace; background: #f1f5f9; padding: 2px 4px; border-radius: 3px; }
pre code { background: none; }
blockquote { border-left: 3px solid #2563eb; padding-left: 12px; color: #1e40af; font-style: italic; }
table { border-collapse: collapse; width: 100%; }
th { background: #2563eb; color: white; padding: 6px 10px; text-align: left; }
td { padding: 6px 10px; border-bottom: 1px solid #e5e7eb; }
"""


def export_epub(full_markdown: str, output_path: Path, title: str = "StudyCraft Guide") -> Path:
    """Export Markdown text to an EPUB file."""
    from ebooklib import epub  # type: ignore

    book = epub.EpubBook()
    book.set_identifier("studycraft-guide")
    book.set_title(title)
    book.set_language("en")
    book.add_author("StudyCraft")

    # CSS
    css = epub.EpubItem(uid="style", file_name="style/default.css", media_type="text/css", content=_EPUB_CSS.encode())
    book.add_item(css)

    # Split into chapters on "# " headings
    raw_chapters = re.split(r"(?=^# )", full_markdown, flags=re.MULTILINE)
    spine = ["nav"]
    toc = []

    for i, ch_md in enumerate(raw_chapters):
        ch_md = ch_md.strip()
        if not ch_md:
            continue

        # Extract title from first line
        first_line = ch_md.splitlines()[0].lstrip("# ").strip()
        file_name = f"ch{i:02d}.xhtml"

        html_body = md_lib.markdown(ch_md, extensions=["tables", "fenced_code"])
        ch_item = epub.EpubHtml(title=first_line, file_name=file_name, lang="en")
        ch_item.content = f"<html><body>{html_body}</body></html>".encode()
        ch_item.add_item(css)

        book.add_item(ch_item)
        spine.append(ch_item)
        toc.append(epub.Link(file_name, first_line, f"ch{i:02d}"))

    book.toc = toc
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(str(output_path), book)
    console.print(f"[green]EPUB[/green]     -> {output_path}")
    return output_path
