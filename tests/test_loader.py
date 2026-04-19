"""Tests for studycraft.loader."""

from pathlib import Path

import pytest

from studycraft.loader import load_document, supported_extensions, SUPPORTED


@pytest.fixture
def tmp_txt(tmp_path: Path) -> Path:
    p = tmp_path / "sample.txt"
    p.write_text("Chapter 1: Hello World\nThis is a test document.", encoding="utf-8")
    return p


@pytest.fixture
def tmp_md(tmp_path: Path) -> Path:
    p = tmp_path / "sample.md"
    p.write_text("# Chapter 1\n\nMarkdown content here.", encoding="utf-8")
    return p


def test_supported_extensions():
    exts = supported_extensions()
    assert ".pdf" in exts
    assert ".docx" in exts
    assert ".txt" in exts
    assert ".md" in exts
    assert ".rtf" in exts


def test_load_txt(tmp_txt: Path):
    text = load_document(tmp_txt)
    assert "Hello World" in text
    assert "test document" in text


def test_load_md(tmp_md: Path):
    text = load_document(tmp_md)
    assert "# Chapter 1" in text
    assert "Markdown content" in text


def test_unsupported_format(tmp_path: Path):
    p = tmp_path / "file.xyz"
    p.write_text("data")
    with pytest.raises(ValueError, match="Unsupported"):
        load_document(p)


def test_supported_set_matches_function():
    assert set(supported_extensions()) == SUPPORTED
