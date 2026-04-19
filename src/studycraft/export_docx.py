"""
StudyCraft – DOCX export.

Converts Markdown guide text into a styled .docx file using python-docx.
"""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console

console = Console()


def export_docx(full_markdown: str, output_path: Path) -> Path:
    """Export Markdown text to a styled DOCX file."""
    from docx import Document  # type: ignore
    from docx.shared import Pt, Inches, RGBColor  # type: ignore

    doc = Document()

    # Set default font
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(11)

    for line in full_markdown.splitlines():
        stripped = line.strip()

        if not stripped or stripped == "---":
            continue

        # Headings
        if stripped.startswith("# "):
            p = doc.add_heading(stripped[2:], level=1)
            for run in p.runs:
                run.font.color.rgb = RGBColor(37, 99, 235)
        elif stripped.startswith("## "):
            p = doc.add_heading(stripped[3:], level=2)
            for run in p.runs:
                run.font.color.rgb = RGBColor(30, 58, 138)
        elif stripped.startswith("### "):
            doc.add_heading(stripped[4:], level=3)
        elif stripped.startswith("| ") and "---" not in stripped:
            # Simple table row — skip separator rows
            doc.add_paragraph(stripped, style="List Bullet")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            doc.add_paragraph(stripped[2:], style="List Bullet")
        elif re.match(r"^\d+\.\s", stripped):
            doc.add_paragraph(stripped, style="List Number")
        elif stripped.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.5)
            run = p.add_run(stripped[2:])
            run.italic = True
            run.font.color.rgb = RGBColor(30, 64, 175)
        elif stripped.startswith("```"):
            continue  # skip code fences
        elif stripped.startswith("**") and stripped.endswith("**"):
            p = doc.add_paragraph()
            run = p.add_run(stripped.strip("*"))
            run.bold = True
        else:
            doc.add_paragraph(stripped)

    doc.save(str(output_path))
    console.print(f"[green]\u2713 DOCX[/green]     \u2192 {output_path}")
    return output_path
