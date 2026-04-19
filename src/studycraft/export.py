"""
StudyCraft – Export pipeline.
Markdown → styled HTML → PDF → DOCX → EPUB.
"""

from __future__ import annotations

import re
from pathlib import Path

import markdown as md_lib
from rich.console import Console

from .themes import Theme, get_theme

console = Console()


def _extract_toc(markdown_text: str) -> list[dict]:
    """Extract headings from markdown for TOC generation."""
    entries = []
    for match in re.finditer(r"^(#{1,3})\s+(.+)$", markdown_text, re.MULTILINE):
        level = len(match.group(1))
        title = match.group(2).strip()
        slug = re.sub(r"[^\w\s-]", "", title.lower()).strip().replace(" ", "-")
        entries.append({"level": level, "title": title, "slug": slug})
    return entries


def _build_css(t: Theme) -> str:
    """Generate full CSS from a Theme."""
    return f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: {t.bg}; color: {t.text}; line-height: 1.75; font-size: 16px;
}}
.container {{ max-width: 860px; margin: 0 auto; padding: 3rem 2rem; }}

.cover {{
  background: linear-gradient(135deg, {t.cover_bg_start} 0%, {t.cover_bg_end} 100%);
  color: {t.cover_fg}; padding: 2.5rem 2rem; border-radius: 12px;
  margin-bottom: 3rem; text-align: center; border: 1px solid {t.border};
}}
.cover h1 {{ font-size: 2rem; font-weight: 800; margin-bottom: 0.4rem; color: {t.cover_fg}; border: none; }}
.cover p {{ opacity: 0.85; font-size: 1rem; }}

h1 {{
  color: {t.h1}; font-size: 1.7rem; font-weight: 800;
  border-bottom: 3px solid {t.h1}; padding-bottom: 0.4rem; margin: 3rem 0 1rem;
}}
h2 {{ color: {t.h2}; font-size: 1.25rem; font-weight: 700; margin: 2.2rem 0 0.75rem; }}
h3 {{ color: {t.h3}; font-size: 1.05rem; font-weight: 600; margin: 1.5rem 0 0.5rem; }}
h4 {{ font-size: 1rem; font-weight: 600; margin: 1rem 0 0.4rem; }}

p {{ margin-bottom: 1rem; }}
ul, ol {{ padding-left: 1.75rem; margin-bottom: 1rem; }}
li {{ margin-bottom: 0.35rem; }}
strong {{ font-weight: 700; }}
a {{ color: {t.primary}; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

pre {{
  background: {t.code_bg}; color: {t.code_fg};
  padding: 1.25rem 1.5rem; border-radius: 10px; overflow-x: auto;
  margin: 1.25rem 0; font-size: 0.875rem; line-height: 1.6;
  border: 1px solid {t.border};
}}
code {{
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  background: {t.code_inline_bg}; color: {t.code_inline_fg};
  padding: 0.15em 0.45em; border-radius: 4px; font-size: 0.9em;
}}
pre code {{ background: none; color: inherit; padding: 0; }}

blockquote {{
  border-left: 4px solid {t.quote_border}; background: {t.quote_bg};
  padding: 0.75rem 1.25rem; border-radius: 0 8px 8px 0;
  color: {t.quote_fg}; font-style: italic; margin: 1.25rem 0;
}}

table {{ width: 100%; border-collapse: collapse; margin: 1.25rem 0; font-size: 0.95rem; }}
th {{
  background: {t.th_bg}; color: {t.th_fg};
  padding: 0.6rem 1rem; text-align: left; font-weight: 600;
}}
td {{ padding: 0.55rem 1rem; border-bottom: 1px solid {t.td_border}; }}
tr:nth-child(even) td {{ background: {t.td_alt_bg}; }}

hr {{ border: none; border-top: 2px solid {t.border}; margin: 2.5rem 0; }}

@media print {{
  body {{ font-size: 13px; }}
  .cover {{ break-after: page; }}
  h1 {{ break-before: page; }}
  pre {{ white-space: pre-wrap; }}
  .toc-sidebar {{ display: none; }}
  .main-content {{ margin-left: 0; }}
}}

.toc-sidebar {{
  position: fixed; top: 0; left: 0; width: 260px; height: 100vh;
  background: {t.toc_bg}; border-right: 1px solid {t.toc_border};
  overflow-y: auto; padding: 1.5rem 1rem; font-size: 0.82rem; z-index: 100;
}}
.toc-sidebar h2 {{
  font-size: 0.85rem; color: {t.primary}; margin: 0 0 0.75rem;
  padding-bottom: 0.5rem; border-bottom: 2px solid {t.primary};
}}
.toc-sidebar ul {{ list-style: none; padding-left: 0; margin: 0; }}
.toc-sidebar li {{ margin-bottom: 0.2rem; }}
.toc-sidebar li li {{ padding-left: 0.9rem; }}
.toc-sidebar li li li {{ padding-left: 0.9rem; font-size: 0.78rem; }}
.toc-sidebar a {{
  color: {t.text}; text-decoration: none; display: block;
  padding: 0.2rem 0.4rem; border-radius: 4px; transition: background 0.15s;
}}
.toc-sidebar a:hover {{ background: {t.toc_hover_bg}; color: {t.primary}; }}
.main-content {{ margin-left: 280px; }}
@media (max-width: 900px) {{
  .toc-sidebar {{ display: none; }}
  .main-content {{ margin-left: 0; }}
}}
.toc-sidebar::-webkit-scrollbar {{ width: 4px; }}
.toc-sidebar::-webkit-scrollbar-thumb {{ background: {t.border}; border-radius: 2px; }}
"""


def _build_epub_css(t: Theme) -> str:
    """Generate EPUB CSS from a Theme."""
    return f"""
body {{ font-family: Georgia, serif; line-height: 1.6; color: {t.text}; background: {t.bg}; }}
h1 {{ color: {t.h1}; border-bottom: 2px solid {t.h1}; padding-bottom: 4px; }}
h2 {{ color: {t.h2}; }}
h3 {{ color: {t.h3}; }}
pre {{ background: {t.code_bg}; color: {t.code_fg}; padding: 12px; border-radius: 6px; }}
code {{ font-family: monospace; background: {t.code_inline_bg}; color: {t.code_inline_fg}; padding: 2px 4px; border-radius: 3px; }}
pre code {{ background: none; color: inherit; }}
blockquote {{ border-left: 3px solid {t.quote_border}; padding-left: 12px; color: {t.quote_fg}; font-style: italic; }}
table {{ border-collapse: collapse; width: 100%; }}
th {{ background: {t.th_bg}; color: {t.th_fg}; padding: 6px 10px; text-align: left; }}
td {{ padding: 6px 10px; border-bottom: 1px solid {t.td_border}; }}
"""


# ── Hex helpers for PDF/DOCX ──────────────────────────────────────────────────


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    """Convert '#rrggbb' to (r, g, b). Returns (0,0,0) for non-hex values."""
    h = h.lstrip("#")
    if len(h) != 6:
        return (0, 0, 0)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _strip_emojis(text: str) -> str:
    """Remove emoji characters that break PDF fonts."""
    return re.sub(
        r"[\U0001f300-\U0001f9ff\U00002702-\U000027b0\U0000fe00-\U0000fe0f"
        r"\U0000200d\U00002600-\U000026ff\U00002700-\U000027bf]+",
        "",
        text,
    ).strip()


# ── Main export ───────────────────────────────────────────────────────────────


def export_all(
    full_markdown: str,
    output_dir: Path,
    base_name: str = "StudyCraft_Practice_Guide",
    theme: str | None = None,
) -> dict[str, Path]:
    """Export to .md, .html, .pdf, .docx, .epub. Returns {format: Path}."""
    t = get_theme(theme)
    paths: dict[str, Path] = {}

    # ── Markdown ──────────────────────────────────────────────────────────────
    toc_entries = _extract_toc(full_markdown)
    toc_md = "## Table of Contents\n\n"
    for e in toc_entries:
        indent = "  " * (e["level"] - 1)
        toc_md += f"{indent}- [{e['title']}](#{e['slug']})\n"
    toc_md += "\n---\n\n"
    md_with_toc = toc_md + full_markdown

    md_path = output_dir / f"{base_name}.md"
    md_path.write_text(md_with_toc, encoding="utf-8")
    console.print(f"[green]✓ Markdown[/green] → {md_path}")
    paths["md"] = md_path

    # ── HTML ──────────────────────────────────────────────────────────────────
    md_ext = md_lib.Markdown(
        extensions=["tables", "fenced_code", "toc", "nl2br", "attr_list"],
    )
    html_body = md_ext.convert(full_markdown)
    toc_html = getattr(md_ext, "toc", "")
    html_doc = _wrap(html_body, base_name, t, toc_html)
    html_path = output_dir / f"{base_name}.html"
    html_path.write_text(html_doc, encoding="utf-8")
    console.print(f"[green]✓ HTML[/green]     → {html_path}")
    paths["html"] = html_path

    # ── PDF ───────────────────────────────────────────────────────────────────
    pdf_path = output_dir / f"{base_name}.pdf"
    try:
        _export_pdf(full_markdown, pdf_path, base_name, t)
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
        export_docx(full_markdown, docx_path, t)
        paths["docx"] = docx_path
    except Exception as exc:
        console.print(f"[yellow]\u26a0 DOCX skipped:[/yellow] {exc}")

    # ── EPUB ──────────────────────────────────────────────────────────────────
    try:
        from .export_epub import export_epub

        epub_path = output_dir / f"{base_name}.epub"
        export_epub(
            full_markdown, epub_path, title=base_name.replace("_", " "), theme=t
        )
        paths["epub"] = epub_path
    except Exception as exc:
        console.print(f"[yellow]EPUB skipped:[/yellow] {exc}")

    return paths


# ── PDF export ────────────────────────────────────────────────────────────────


def _export_pdf(full_markdown: str, pdf_path: Path, base_name: str, t: Theme) -> None:
    """Generate a styled PDF from Markdown using fpdf2."""
    import re as _re

    from fpdf import FPDF  # type: ignore

    h1r, h1g, h1b = _hex_to_rgb(t.h1)
    h2r, h2g, h2b = _hex_to_rgb(t.h2)
    h3r, h3g, h3b = _hex_to_rgb(t.h3)
    txr, txg, txb = _hex_to_rgb(t.text)
    mur, mug, mub = _hex_to_rgb(t.muted)
    bgr, bgg, bgb = _hex_to_rgb(t.bg)
    cbr, cbg, cbb = _hex_to_rgb(t.code_bg)
    cfr, cfg, cfb = _hex_to_rgb(t.code_fg)
    brr, brg, brb = _hex_to_rgb(t.border)

    class _PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(mur, mug, mub)
            self.cell(0, 8, base_name.replace("_", " "), align="C")
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(mur, mug, mub)
            self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    pdf = _PDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Cover page
    pdf.add_page()
    pdf.set_fill_color(bgr, bgg, bgb)
    pdf.rect(0, 0, pdf.w, pdf.h, "F")
    pdf.ln(40)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(h1r, h1g, h1b)
    pdf.multi_cell(0, 14, _strip_emojis(base_name.replace("_", " ")), align="C")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(mur, mug, mub)
    pdf.multi_cell(0, 7, "Generated by StudyCraft", align="C")

    # TOC page
    toc_entries = _extract_toc(full_markdown)
    if toc_entries:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(h1r, h1g, h1b)
        pdf.cell(0, 12, "Table of Contents")
        pdf.ln(14)
        for e in toc_entries:
            indent = 6 * (e["level"] - 1)
            if e["level"] == 1:
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(txr, txg, txb)
            elif e["level"] == 2:
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(h2r, h2g, h2b)
            else:
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(mur, mug, mub)
            pdf.cell(indent)
            pdf.multi_cell(0, 6, e["title"])
            pdf.ln(1)

    # Content
    pdf.add_page()
    for line in full_markdown.splitlines():
        stripped = line.strip()

        if stripped.startswith("# "):
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_text_color(h1r, h1g, h1b)
            pdf.ln(6)
            pdf.multi_cell(0, 9, _strip_emojis(stripped[2:]))
            pdf.set_draw_color(h1r, h1g, h1b)
            pdf.line(pdf.get_x() + 10, pdf.get_y(), pdf.w - 10, pdf.get_y())
            pdf.ln(4)
        elif stripped.startswith("## "):
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(h2r, h2g, h2b)
            pdf.ln(4)
            pdf.multi_cell(0, 8, _strip_emojis(stripped[3:]))
            pdf.ln(2)
        elif stripped.startswith("### "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(h3r, h3g, h3b)
            pdf.ln(3)
            pdf.multi_cell(0, 7, _strip_emojis(stripped[4:]))
            pdf.ln(2)
        elif stripped.startswith("```"):
            pdf.set_font("Courier", "", 9)
            pdf.set_text_color(cfr, cfg, cfb)
            pdf.set_fill_color(cbr, cbg, cbb)
        elif stripped == "---":
            pdf.ln(4)
            pdf.set_draw_color(brr, brg, brb)
            pdf.line(pdf.get_x() + 10, pdf.get_y(), pdf.w - 10, pdf.get_y())
            pdf.ln(4)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(txr, txg, txb)
            pdf.cell(8)
            pdf.multi_cell(0, 6, _strip_emojis(f"\u2022 {stripped[2:]}"))
            pdf.ln(1)
        elif _re.match(r"^\d+\.", stripped):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(txr, txg, txb)
            pdf.cell(4)
            pdf.multi_cell(0, 6, _strip_emojis(stripped))
            pdf.ln(1)
        elif stripped:
            if pdf.font_family == "Courier":
                pdf.cell(4)
                pdf.multi_cell(0, 5, _strip_emojis(stripped), fill=True)
            else:
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(txr, txg, txb)
                clean = _re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)
                pdf.multi_cell(0, 6, _strip_emojis(clean))
                pdf.ln(1)
        else:
            if pdf.font_family == "Courier":
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(txr, txg, txb)
            pdf.ln(3)

    pdf.output(str(pdf_path))


# ── HTML wrapper ──────────────────────────────────────────────────────────────


def _wrap(body: str, title: str, t: Theme, toc_html: str = "") -> str:
    clean_title = title.replace("_", " ")
    css = _build_css(t)
    toc_sidebar = ""
    if toc_html:
        toc_sidebar = (
            f'<nav class="toc-sidebar"><h2>\U0001f5d2 Contents</h2>{toc_html}</nav>'
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{clean_title} — StudyCraft</title>
<style>{css}</style>
</head>
<body>
{toc_sidebar}
<div class="main-content">
<div class="container">
<div class="cover">
  <h1>\U0001f4d6 {clean_title}</h1>
  <p>Generated by <strong>StudyCraft</strong> · AI-powered practice guides</p>
</div>
{body}
</div>
</div>
<script>
(function() {{
  const links = document.querySelectorAll('.toc-sidebar a');
  if (!links.length) return;
  const observer = new IntersectionObserver(entries => {{
    entries.forEach(e => {{
      if (e.isIntersecting) {{
        links.forEach(l => {{ l.style.fontWeight = ''; l.style.color = ''; }});
        const id = e.target.id;
        const active = document.querySelector('.toc-sidebar a[href="#' + id + '"]');
        if (active) {{ active.style.fontWeight = '700'; active.style.color = '{t.primary}'; }}
      }}
    }});
  }}, {{ rootMargin: '-80px 0px -70% 0px' }});
  document.querySelectorAll('h1[id], h2[id], h3[id]').forEach(h => observer.observe(h));
}})()
</script>
</body>
</html>"""
