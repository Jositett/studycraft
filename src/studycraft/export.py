"""
StudyCraft – Export pipeline.
Markdown → styled HTML → PDF.
"""

from __future__ import annotations

from pathlib import Path

import markdown as md_lib
from rich.console import Console

console = Console()

_CSS = """
:root {
  --primary: #2563eb;
  --primary-light: #eff6ff;
  --accent: #7c3aed;
  --bg: #f9fafb;
  --surface: #ffffff;
  --text: #111827;
  --muted: #6b7280;
  --border: #e5e7eb;
  --code-bg: #1e293b;
  --code-fg: #e2e8f0;
  --green: #16a34a;
  --yellow: #d97706;
  --red: #dc2626;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.75;
  font-size: 16px;
}

.container {
  max-width: 860px;
  margin: 0 auto;
  padding: 3rem 2rem;
}

/* ── Cover strip ── */
.cover {
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
  color: white;
  padding: 2.5rem 2rem;
  border-radius: 12px;
  margin-bottom: 3rem;
  text-align: center;
}
.cover h1 { font-size: 2rem; font-weight: 800; margin-bottom: 0.4rem; }
.cover p { opacity: 0.85; font-size: 1rem; }

/* ── Headings ── */
h1 {
  color: var(--primary);
  font-size: 1.7rem;
  font-weight: 800;
  border-bottom: 3px solid var(--primary);
  padding-bottom: 0.4rem;
  margin: 3rem 0 1rem;
}
h2 {
  color: #1e3a8a;
  font-size: 1.25rem;
  font-weight: 700;
  margin: 2.2rem 0 0.75rem;
}
h3 {
  color: var(--accent);
  font-size: 1.05rem;
  font-weight: 600;
  margin: 1.5rem 0 0.5rem;
}
h4 { font-size: 1rem; font-weight: 600; margin: 1rem 0 0.4rem; }

/* ── Body text ── */
p { margin-bottom: 1rem; }
ul, ol { padding-left: 1.75rem; margin-bottom: 1rem; }
li { margin-bottom: 0.35rem; }
strong { font-weight: 700; }
a { color: var(--primary); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── Code ── */
pre {
  background: var(--code-bg);
  color: var(--code-fg);
  padding: 1.25rem 1.5rem;
  border-radius: 10px;
  overflow-x: auto;
  margin: 1.25rem 0;
  font-size: 0.875rem;
  line-height: 1.6;
}
code {
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  background: #f1f5f9;
  color: #7c3aed;
  padding: 0.15em 0.45em;
  border-radius: 4px;
  font-size: 0.9em;
}
pre code { background: none; color: inherit; padding: 0; }

/* ── Blockquotes ── */
blockquote {
  border-left: 4px solid var(--primary);
  background: var(--primary-light);
  padding: 0.75rem 1.25rem;
  border-radius: 0 8px 8px 0;
  color: #1e40af;
  font-style: italic;
  margin: 1.25rem 0;
}

/* ── Tables ── */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 1.25rem 0;
  font-size: 0.95rem;
}
th {
  background: var(--primary);
  color: white;
  padding: 0.6rem 1rem;
  text-align: left;
  font-weight: 600;
}
td {
  padding: 0.55rem 1rem;
  border-bottom: 1px solid var(--border);
}
tr:nth-child(even) td { background: #f8fafc; }

/* ── HR ── */
hr {
  border: none;
  border-top: 2px solid var(--border);
  margin: 2.5rem 0;
}

/* ── Emoji section labels (🟢 🟡 🔴) ── */
h3:has(+ ul) { margin-top: 1.25rem; }

/* ── Print ── */
@media print {
  body { font-size: 13px; }
  .cover { break-after: page; }
  h1 { break-before: page; }
  pre { white-space: pre-wrap; }
}
"""


def export_all(
    full_markdown: str,
    output_dir: Path,
    base_name: str = "StudyCraft_Practice_Guide",
) -> dict[str, Path]:
    """Export to .md, .html, .pdf. Returns {format: Path}."""
    paths: dict[str, Path] = {}

    # ── Markdown ──────────────────────────────────────────────────────────────
    md_path = output_dir / f"{base_name}.md"
    md_path.write_text(full_markdown, encoding="utf-8")
    console.print(f"[green]✓ Markdown[/green] → {md_path}")
    paths["md"] = md_path

    # ── HTML ──────────────────────────────────────────────────────────────────
    html_body = md_lib.markdown(
        full_markdown,
        extensions=["tables", "fenced_code", "toc", "nl2br", "attr_list"],
    )
    html_doc = _wrap(html_body, base_name)
    html_path = output_dir / f"{base_name}.html"
    html_path.write_text(html_doc, encoding="utf-8")
    console.print(f"[green]✓ HTML[/green]     → {html_path}")
    paths["html"] = html_path

    # ── PDF ───────────────────────────────────────────────────────────────────
    pdf_path = output_dir / f"{base_name}.pdf"
    try:
        import weasyprint  # type: ignore
        weasyprint.HTML(string=html_doc).write_pdf(str(pdf_path))
        console.print(f"[green]✓ PDF[/green]      → {pdf_path}")
        paths["pdf"] = pdf_path
    except Exception as exc:
        console.print(
            f"[yellow]⚠ PDF skipped:[/yellow] {exc}\n"
            "  Tip: open the HTML in Chrome → Ctrl+P → Save as PDF"
        )

    # ── DOCX ──────────────────────────────────────────────────────────────────
    try:
        from .export_docx import export_docx
        docx_path = output_dir / f"{base_name}.docx"
        export_docx(full_markdown, docx_path)
        paths["docx"] = docx_path
    except Exception as exc:
        console.print(f"[yellow]\u26a0 DOCX skipped:[/yellow] {exc}")

    return paths


def _wrap(body: str, title: str) -> str:
    clean_title = title.replace("_", " ")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{clean_title} — StudyCraft</title>
<style>{_CSS}</style>
</head>
<body>
<div class="container">
<div class="cover">
  <h1>📖 {clean_title}</h1>
  <p>Generated by <strong>StudyCraft</strong> · AI-powered practice guides</p>
</div>
{body}
</div>
</body>
</html>"""
