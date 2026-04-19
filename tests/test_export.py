"""Tests for studycraft.export."""

from pathlib import Path

from studycraft.export import export_all, _extract_toc, _build_css, _build_epub_css
from studycraft.themes import DARK


_SAMPLE_MD = """\
# 📖 Practice Guide — Test Subject
## Chapter 1: Basics

Some content here.

| Term | Definition |
|------|-----------| 
| Foo  | A test term |

```python
x = 42
```
"""


def test_export_creates_all_formats(tmp_path: Path):
    paths = export_all(_SAMPLE_MD, tmp_path, base_name="Test_Guide")
    for fmt in ("md", "html", "docx", "epub"):
        assert fmt in paths, f"Missing format: {fmt}"
        assert paths[fmt].exists(), f"{fmt} file not created"
        assert paths[fmt].stat().st_size > 0, f"{fmt} file is empty"


def test_md_has_toc_prepended(tmp_path: Path):
    paths = export_all(_SAMPLE_MD, tmp_path, base_name="Test_Guide")
    content = paths["md"].read_text(encoding="utf-8")
    assert content.startswith("## Table of Contents")
    assert "x = 42" in content


def test_html_has_syntax_highlighting(tmp_path: Path):
    paths = export_all(_SAMPLE_MD, tmp_path, base_name="Test_Guide")
    html = paths["html"].read_text(encoding="utf-8")
    # codehilite wraps code blocks in a div with class="codehilite"
    assert "codehilite" in html
    # Pygments tokenizes Python: 'x' -> .n, '=' -> .o, '42' -> .mi
    assert '<span class="mi">42</span>' in html or 'class="mi"' in html


def test_html_has_copy_button(tmp_path: Path):
    paths = export_all(_SAMPLE_MD, tmp_path, base_name="Test_Guide")
    html = paths["html"].read_text(encoding="utf-8")
    assert "copy-btn" in html
    assert "navigator.clipboard.writeText" in html
    assert "Copied!" in html


def test_html_has_toc_sidebar(tmp_path: Path):
    paths = export_all(_SAMPLE_MD, tmp_path, base_name="Test_Guide")
    html = paths["html"].read_text(encoding="utf-8")
    assert "toc-sidebar" in html
    assert "Contents" in html


def test_html_has_themed_css(tmp_path: Path):
    paths = export_all(_SAMPLE_MD, tmp_path, base_name="Test_Guide", theme="dracula")
    html = paths["html"].read_text(encoding="utf-8")
    # Dracula bg color should appear in CSS
    assert "#282a36" in html
    # Dracula keyword color
    assert "#ff79c6" in html


def test_html_structure(tmp_path: Path):
    paths = export_all(_SAMPLE_MD, tmp_path, base_name="Test_Guide")
    html = paths["html"].read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "<title>" in html
    assert "StudyCraft" in html
    assert "<table>" in html


def test_export_base_name(tmp_path: Path):
    paths = export_all(_SAMPLE_MD, tmp_path, base_name="Custom_Name")
    assert paths["md"].name == "Custom_Name.md"
    assert paths["html"].name == "Custom_Name.html"


def test_extract_toc():
    entries = _extract_toc("# Heading 1\n## Sub 1\n### Sub Sub\n")
    assert len(entries) == 3
    assert entries[0]["level"] == 1
    assert entries[0]["title"] == "Heading 1"
    assert entries[1]["level"] == 2
    assert entries[2]["level"] == 3


def test_build_css_contains_syntax_classes():
    css = _build_css(DARK)
    assert ".codehilite .k" in css
    assert ".codehilite .s" in css
    assert ".codehilite .nc" in css
    assert ".copy-btn" in css
    assert DARK.syn_keyword in css
    assert DARK.syn_string in css


def test_build_epub_css_contains_syntax_classes():
    css = _build_epub_css(DARK)
    assert ".codehilite .k" in css
    assert ".codehilite .nf" in css
    assert DARK.syn_keyword in css
