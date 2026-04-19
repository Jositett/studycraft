"""Tests for studycraft.export."""

from pathlib import Path

from studycraft.export import export_all


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


def test_export_creates_md_and_html(tmp_path: Path):
    paths = export_all(_SAMPLE_MD, tmp_path, base_name="Test_Guide")
    assert "md" in paths
    assert "html" in paths
    assert paths["md"].exists()
    assert paths["html"].exists()


def test_md_content_matches(tmp_path: Path):
    paths = export_all(_SAMPLE_MD, tmp_path, base_name="Test_Guide")
    content = paths["md"].read_text(encoding="utf-8")
    assert "Practice Guide" in content
    assert "x = 42" in content


def test_html_has_structure(tmp_path: Path):
    paths = export_all(_SAMPLE_MD, tmp_path, base_name="Test_Guide")
    html = paths["html"].read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "<title>" in html
    assert "StudyCraft" in html
    assert "<table>" in html


def test_html_has_code_block(tmp_path: Path):
    paths = export_all(_SAMPLE_MD, tmp_path, base_name="Test_Guide")
    html = paths["html"].read_text(encoding="utf-8")
    assert "x = 42" in html


def test_export_base_name(tmp_path: Path):
    paths = export_all(_SAMPLE_MD, tmp_path, base_name="Custom_Name")
    assert paths["md"].name == "Custom_Name.md"
    assert paths["html"].name == "Custom_Name.html"


def test_export_creates_docx(tmp_path: Path):
    paths = export_all(_SAMPLE_MD, tmp_path, base_name="Test_Guide")
    assert "docx" in paths
    assert paths["docx"].exists()
    assert paths["docx"].name == "Test_Guide.docx"
