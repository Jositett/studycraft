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
  border: 1px solid {t.border}; position: relative;
}}
code {{
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  background: {t.code_inline_bg}; color: {t.code_inline_fg};
  padding: 0.15em 0.45em; border-radius: 4px; font-size: 0.9em;
}}
pre code {{ background: none; color: inherit; padding: 0; }}

/* Copy button */
.copy-btn {{
  position: absolute; top: 8px; right: 8px;
  background: {t.surface}; color: {t.muted}; border: 1px solid {t.border};
  border-radius: 6px; padding: 4px 10px; font-size: 0.75rem;
  cursor: pointer; opacity: 0; transition: opacity 0.2s, background 0.15s;
  font-family: inherit; z-index: 1;
}}
pre:hover .copy-btn {{ opacity: 1; }}
.copy-btn:hover {{ background: {t.border}; color: {t.text}; }}
.copy-btn.copied {{ color: {t.primary}; }}

/* Syntax highlighting (Pygments codehilite classes) */
.codehilite {{ background: {t.code_bg}; border-radius: 10px; }}
.codehilite pre {{ background: transparent; border: none; margin: 0; }}
.codehilite .k, .codehilite .kn, .codehilite .kd, .codehilite .kc,
.codehilite .kr, .codehilite .kt {{ color: {t.syn_keyword}; font-weight: 600; }}
.codehilite .s, .codehilite .s1, .codehilite .s2, .codehilite .sa,
.codehilite .sb, .codehilite .sc, .codehilite .sd, .codehilite .se,
.codehilite .sh, .codehilite .si, .codehilite .sr, .codehilite .ss {{ color: {t.syn_string}; }}
.codehilite .c, .codehilite .c1, .codehilite .cm, .codehilite .cs,
.codehilite .ch, .codehilite .cp, .codehilite .cpf {{ color: {t.syn_comment}; font-style: italic; }}
.codehilite .nf, .codehilite .fm, .codehilite .nv {{ color: {t.syn_function}; }}
.codehilite .nc, .codehilite .nn {{ color: {t.syn_class}; font-weight: 600; }}
.codehilite .mi, .codehilite .mf, .codehilite .mh, .codehilite .mo,
.codehilite .mb, .codehilite .il {{ color: {t.syn_number}; }}
.codehilite .o, .codehilite .ow {{ color: {t.syn_operator}; }}
.codehilite .nb, .codehilite .bp {{ color: {t.syn_builtin}; }}
.codehilite .p {{ color: {t.code_fg}; }}
.codehilite .n, .codehilite .na, .codehilite .nd, .codehilite .ni,
.codehilite .ne, .codehilite .nl, .codehilite .no, .codehilite .nt {{ color: {t.code_fg}; }}
.codehilite .gd {{ color: #f44747; }}
.codehilite .gi {{ color: #4ec9b0; }}

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
.codehilite {{ background: {t.code_bg}; border-radius: 6px; }}
.codehilite pre {{ background: transparent; border: none; margin: 0; }}
.codehilite .k, .codehilite .kn, .codehilite .kd {{ color: {t.syn_keyword}; font-weight: bold; }}
.codehilite .s, .codehilite .s1, .codehilite .s2 {{ color: {t.syn_string}; }}
.codehilite .c, .codehilite .c1, .codehilite .cm {{ color: {t.syn_comment}; font-style: italic; }}
.codehilite .nf, .codehilite .fm {{ color: {t.syn_function}; }}
.codehilite .nc, .codehilite .nn {{ color: {t.syn_class}; }}
.codehilite .mi, .codehilite .mf {{ color: {t.syn_number}; }}
.codehilite .nb, .codehilite .bp {{ color: {t.syn_builtin}; }}
.codehilite .o, .codehilite .ow {{ color: {t.syn_operator}; }}
"""


# ── Hex helpers for PDF/DOCX ──────────────────────────────────────────────────


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    """Convert '#rrggbb' to (r, g, b). Returns (0,0,0) for non-hex values."""
    h = h.lstrip("#")
    if len(h) != 6:
        return (0, 0, 0)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _strip_emojis(text: str) -> str:
    """Remove emoji and non-latin characters that break PDF fonts."""
    return re.sub(
        r"[^\x00-\xFF]",  # remove anything outside latin-1 range
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
    # Strip emoji from base_name for PDF/DOCX compatibility
    safe_base_name = _strip_emojis(base_name)

    # ── Markdown ──────────────────────────────────────────────────────────────
    toc_entries = _extract_toc(full_markdown)
    toc_md = "## Table of Contents\n\n"
    for e in toc_entries:
        indent = "  " * (e["level"] - 1)
        toc_md += f"{indent}- [{e['title']}](#{e['slug']})\n"
    toc_md += "\n---\n\n"
    md_with_toc = toc_md + full_markdown

    md_path = output_dir / f"{safe_base_name}.md"
    md_path.write_text(md_with_toc, encoding="utf-8")
    console.print(f"[green]✓ Markdown[/green] → {md_path}")
    paths["md"] = md_path

    # ── HTML ──────────────────────────────────────────────────────────────────
    md_ext = md_lib.Markdown(
        extensions=["tables", "fenced_code", "codehilite", "toc", "nl2br", "attr_list"],
        extension_configs={
            "codehilite": {"css_class": "codehilite", "guess_lang": True, "noclasses": False},
        },
    )
    html_body = md_ext.convert(full_markdown)
    toc_html = getattr(md_ext, "toc", "")
    html_doc = _wrap(html_body, base_name, t, toc_html)
    html_path = output_dir / f"{safe_base_name}.html"
    html_path.write_text(html_doc, encoding="utf-8")
    console.print(f"[green]✓ HTML[/green]     → {html_path}")
    paths["html"] = html_path

    # ── PDF ───────────────────────────────────────────────────────────────────
    pdf_path = output_dir / f"{safe_base_name}.pdf"
    print_html = _build_print_html(full_markdown, safe_base_name, t)
    _pdf_ok = False
    for _attempt in [
        lambda: _export_pdf_playwright(print_html, pdf_path),
        lambda: _export_pdf_xhtml2pdf(print_html, pdf_path),
        lambda: _export_pdf_fpdf2(full_markdown, pdf_path, safe_base_name, t),
    ]:
        try:
            _attempt()
            try:
                _inject_pdf_bookmarks(pdf_path, toc_entries)
            except Exception:
                pass  # bookmarks are best-effort
            console.print(f"[green]✓ PDF[/green]      → {pdf_path}")
            paths["pdf"] = pdf_path
            _pdf_ok = True
            break
        except Exception:
            pass
    if not _pdf_ok:
        console.print(
            "[yellow]⚠ PDF skipped[/yellow] — all renderers failed.\n"
            "  Tip: open the HTML in Chrome → Ctrl+P → Save as PDF"
        )

    # ── DOCX ──────────────────────────────────────────────────────────────────
    try:
        from .export_docx import export_docx

        docx_path = output_dir / f"{safe_base_name}.docx"
        export_docx(full_markdown, docx_path, t)
        paths["docx"] = docx_path
    except Exception as exc:
        console.print(f"[yellow]\u26a0 DOCX skipped:[/yellow] {exc}")

    # ── EPUB ──────────────────────────────────────────────────────────────────
    try:
        from .export_epub import export_epub

        epub_path = output_dir / f"{safe_base_name}.epub"
        export_epub(full_markdown, epub_path, title=safe_base_name.replace("_", " "), theme=t)
        paths["epub"] = epub_path
    except Exception as exc:
        console.print(f"[yellow]EPUB skipped:[/yellow] {exc}")

    return paths


# ── PDF bookmark injection (shared) ──────────────────────────────────────────


def _inject_pdf_bookmarks(pdf_path: Path, toc_entries: list[dict]) -> None:
    """Add PDF outline/bookmarks to an existing PDF using pypdf."""
    import pypdf
    from pypdf.generic import NameObject

    reader = pypdf.PdfReader(str(pdf_path))
    writer = pypdf.PdfWriter()
    writer.append(reader)

    # Map heading slugs to page numbers by scanning page text
    slug_to_page: dict[str, int] = {}
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        for entry in toc_entries:
            if entry["title"] in text and entry["slug"] not in slug_to_page:
                slug_to_page[entry["slug"]] = page_num

    # Build outline — track parent handles per level
    parents: dict[int, object] = {}
    for entry in toc_entries:
        level = entry["level"]
        page_num = slug_to_page.get(entry["slug"], 0)
        title = re.sub(r"[^\x20-\x7E]", "", entry["title"]).strip()  # ASCII only for PDF outline
        parent = parents.get(level - 1)
        handle = writer.add_outline_item(title, page_num, parent=parent)
        parents[level] = handle
        # Clear deeper levels when we go back up
        for deeper in list(parents):
            if deeper > level:
                del parents[deeper]

    # Set PDF viewer to show bookmarks panel on open
    writer._root_object.update({NameObject("/PageMode"): NameObject("/UseOutlines")})

    with pdf_path.open("wb") as f:
        writer.write(f)


# ── Print-optimized HTML for PDF renderers ────────────────────────────────────


def _build_print_html(full_markdown: str, title: str, t: Theme) -> str:
    """Build a print-optimized HTML document: no JS, no fixed sidebar,
    rgba/gradient converted, inline TOC page, xhtml2pdf-safe CSS."""

    def _rgba_to_hex(color: str) -> str:
        """Convert rgba(r,g,b,a) to a blended hex against a dark/light bg."""
        m = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)", color)
        if not m:
            return color
        r, g, b, a = int(m[1]), int(m[2]), int(m[3]), float(m[4])
        bg_r, bg_g, bg_b = _hex_to_rgb(t.bg)
        br = int(r * a + bg_r * (1 - a))
        bg2 = int(g * a + bg_g * (1 - a))
        bb = int(b * a + bg_b * (1 - a))
        return f"#{br:02x}{bg2:02x}{bb:02x}"

    bg = t.bg
    text = t.text
    h1 = t.h1
    h2 = t.h2
    h3 = t.h3
    primary = t.primary
    muted = t.muted
    border = t.border
    code_bg = t.code_bg
    code_fg = t.code_fg
    code_inline_bg = _rgba_to_hex(t.code_inline_bg)
    code_inline_fg = t.code_inline_fg
    quote_border = t.quote_border
    quote_bg = _rgba_to_hex(t.quote_bg)
    quote_fg = t.quote_fg
    th_bg = t.th_bg
    th_fg = t.th_fg
    td_border = t.td_border
    td_alt_bg = _rgba_to_hex(t.td_alt_bg) if t.td_alt_bg.startswith("rgba") else t.td_alt_bg
    cover_bg = _rgba_to_hex(t.cover_bg_start) if t.cover_bg_start.startswith("rgba") else t.cover_bg_start
    cover_fg = t.cover_fg
    syn_keyword = t.syn_keyword
    syn_string = t.syn_string
    syn_comment = t.syn_comment
    syn_function = t.syn_function
    syn_class = t.syn_class
    syn_number = t.syn_number
    syn_operator = t.syn_operator
    syn_builtin = t.syn_builtin

    css = f"""
@page {{ size: A4; margin: 20mm 15mm; }}
body {{ font-family: Helvetica, Arial, sans-serif; background: {bg}; color: {text}; font-size: 11pt; line-height: 1.6; }}
.cover {{ background: {cover_bg}; color: {cover_fg}; padding: 40pt 30pt; text-align: center; margin-bottom: 30pt; }}
.cover h1 {{ font-size: 24pt; font-weight: bold; color: {cover_fg}; border: none; margin: 0 0 8pt; }}
.cover p {{ font-size: 11pt; color: {cover_fg}; margin: 0; }}
.toc-page {{ page-break-after: always; margin-bottom: 20pt; }}
.toc-page h2 {{ font-size: 16pt; color: {h1}; border-bottom: 2pt solid {h1}; padding-bottom: 4pt; margin-bottom: 12pt; }}
.toc-page ul {{ list-style: none; padding: 0; margin: 0; }}
.toc-page li {{ padding: 2pt 0; }}
.toc-page li.level-1 {{ font-weight: bold; font-size: 10pt; color: {text}; }}
.toc-page li.level-2 {{ padding-left: 16pt; font-size: 9pt; color: {h2}; }}
.toc-page li.level-3 {{ padding-left: 32pt; font-size: 8pt; color: {muted}; }}
.toc-page a {{ color: inherit; text-decoration: none; }}
h1 {{ font-size: 18pt; font-weight: bold; color: {h1}; border-bottom: 2pt solid {h1}; padding-bottom: 3pt; margin: 20pt 0 8pt; page-break-before: always; }}
h1:first-of-type {{ page-break-before: avoid; }}
h2 {{ font-size: 14pt; font-weight: bold; color: {h2}; margin: 14pt 0 6pt; }}
h3 {{ font-size: 12pt; font-weight: bold; color: {h3}; margin: 10pt 0 4pt; }}
h4 {{ font-size: 11pt; font-weight: bold; margin: 8pt 0 3pt; }}
p {{ margin: 0 0 8pt; }}
ul, ol {{ padding-left: 18pt; margin: 0 0 8pt; }}
li {{ margin-bottom: 3pt; }}
strong {{ font-weight: bold; }}
em {{ font-style: italic; }}
a {{ color: {primary}; }}
pre {{ background: {code_bg}; color: {code_fg}; padding: 10pt 12pt; font-size: 8pt; line-height: 1.4; border: 1pt solid {border}; margin: 8pt 0; overflow: hidden; }}
code {{ font-family: Courier, monospace; background: {code_inline_bg}; color: {code_inline_fg}; font-size: 9pt; padding: 1pt 3pt; }}
pre code {{ background: none; color: inherit; padding: 0; font-size: 8pt; }}
blockquote {{ border-left: 3pt solid {quote_border}; background: {quote_bg}; padding: 6pt 10pt; color: {quote_fg}; font-style: italic; margin: 8pt 0; }}
table {{ width: 100%; border-collapse: collapse; margin: 8pt 0; font-size: 9pt; }}
th {{ background: {th_bg}; color: {th_fg}; padding: 5pt 8pt; text-align: left; font-weight: bold; }}
td {{ padding: 4pt 8pt; border-bottom: 1pt solid {td_border}; }}
tr.alt td {{ background: {td_alt_bg}; }}
hr {{ border: none; border-top: 1pt solid {border}; margin: 12pt 0; }}
.codehilite {{ background: {code_bg}; padding: 10pt 12pt; margin: 8pt 0; border: 1pt solid {border}; }}
.codehilite pre {{ background: transparent; border: none; margin: 0; padding: 0; }}
.codehilite .k, .codehilite .kn, .codehilite .kd, .codehilite .kc, .codehilite .kr, .codehilite .kt {{ color: {syn_keyword}; font-weight: bold; }}
.codehilite .s, .codehilite .s1, .codehilite .s2 {{ color: {syn_string}; }}
.codehilite .c, .codehilite .c1, .codehilite .cm {{ color: {syn_comment}; font-style: italic; }}
.codehilite .nf, .codehilite .fm {{ color: {syn_function}; }}
.codehilite .nc, .codehilite .nn {{ color: {syn_class}; }}
.codehilite .mi, .codehilite .mf {{ color: {syn_number}; }}
.codehilite .nb, .codehilite .bp {{ color: {syn_builtin}; }}
.codehilite .o, .codehilite .ow {{ color: {syn_operator}; }}
"""

    # Convert markdown to HTML body
    md_ext = md_lib.Markdown(
        extensions=["tables", "fenced_code", "codehilite", "toc", "nl2br", "attr_list"],
        extension_configs={
            "codehilite": {"css_class": "codehilite", "guess_lang": True, "noclasses": False},
        },
    )
    html_body = md_ext.convert(full_markdown)

    # Inline TOC page
    toc_entries = _extract_toc(full_markdown)
    toc_items = ""
    for e in toc_entries:
        safe_title = re.sub(r"[^\x20-\x7E]", "", e["title"]).strip()
        toc_items += f'<li class="level-{e["level"]}"><a href="#{e["slug"]}">{safe_title}</a></li>\n'

    clean_title = re.sub(r"[^\x20-\x7E ]", "", title.replace("_", " ")).strip()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{clean_title}</title>
<style>{css}</style>
</head>
<body>
<div class="cover">
  <h1>{clean_title}</h1>
  <p>Generated by StudyCraft</p>
</div>
<div class="toc-page">
  <h2>Table of Contents</h2>
  <ul>{toc_items}</ul>
</div>
{html_body}
</body>
</html>"""


# ── PDF export (playwright) ────────────────────────────────────────────────────


def _export_pdf_playwright(html_content: str, pdf_path: Path) -> None:
    """Render HTML to PDF using headless Chromium (perfect emoji + CSS support)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        page.evaluate("""
            const toc = document.querySelector('.toc-sidebar');
            if (toc) toc.style.display = 'none';
            const main = document.querySelector('.main-content');
            if (main) main.style.marginLeft = '0';
        """)
        page.pdf(
            path=str(pdf_path),
            format="A4",
            margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
            print_background=True,
        )
        browser.close()


# ── PDF export (xhtml2pdf fallback) ─────────────────────────────────────────


def _export_pdf_xhtml2pdf(html_content: str, pdf_path: Path) -> None:
    """Render HTML to PDF using xhtml2pdf (pure Python, full Unicode/emoji support)."""
    from xhtml2pdf import pisa  # type: ignore

    with pdf_path.open("wb") as f:
        result = pisa.CreatePDF(html_content.encode("utf-8"), dest=f, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"xhtml2pdf error: {result.err}")


# ── PDF export (fpdf2 last-resort) ────────────────────────────────────────────


def _export_pdf_fpdf2(full_markdown: str, pdf_path: Path, base_name: str, t: Theme) -> None:
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
        toc_sidebar = f'<nav class="toc-sidebar"><h2>\U0001f5d2 Contents</h2>{toc_html}</nav>'
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

// Copy buttons on code blocks
document.querySelectorAll('pre').forEach(pre => {{
  const btn = document.createElement('button');
  btn.className = 'copy-btn';
  btn.textContent = 'Copy';
  btn.addEventListener('click', () => {{
    const code = pre.querySelector('code');
    const text = code ? code.textContent : pre.textContent;
    navigator.clipboard.writeText(text).then(() => {{
      btn.textContent = 'Copied!';
      btn.classList.add('copied');
      setTimeout(() => {{ btn.textContent = 'Copy'; btn.classList.remove('copied'); }}, 2000);
    }});
  }});
  pre.style.position = 'relative';
  pre.appendChild(btn);
}});
</script>
</body>
</html>"""
