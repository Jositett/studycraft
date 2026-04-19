"""
StudyCraft – Document loader.

Supports: .pdf  .docx  .txt  .md  .rtf  .epub
Returns raw text regardless of source format.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

console = Console()

SUPPORTED = {".pdf", ".docx", ".txt", ".md", ".rtf", ".epub"}


def load_document(path: Path) -> str:
    """
    Load any supported document and return its full text.
    Raises ValueError for unsupported types.
    """
    suffix = path.suffix.lower()

    if suffix not in SUPPORTED:
        raise ValueError(
            f"Unsupported file type '{suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED))}"
        )

    console.print(f"[cyan]📄 Loading:[/cyan] {path.name}  [dim]({suffix})[/dim]")

    if suffix == ".pdf":
        return _load_pdf(path)
    elif suffix == ".docx":
        return _load_docx(path)
    elif suffix == ".rtf":
        return _load_rtf(path)
    elif suffix == ".epub":
        return _load_epub(path)
    else:  # .txt / .md
        return path.read_text(encoding="utf-8", errors="replace")


# ── Format-specific loaders ───────────────────────────────────────────────────

def _load_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)
        else:
            console.print(f"  [dim yellow]⚠ Page {i+1} yielded no text (may be scanned image)[/dim yellow]")
    return "\n".join(pages)


def _load_docx(path: Path) -> str:
    from docx import Document  # type: ignore

    doc = Document(str(path))
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())


def _load_rtf(path: Path) -> str:
    from striprtf.striprtf import rtf_to_text  # type: ignore

    raw = path.read_text(encoding="utf-8", errors="replace")
    return rtf_to_text(raw)


def _load_epub(path: Path) -> str:
    from ebooklib import epub  # type: ignore
    from ebooklib import ITEM_DOCUMENT  # type: ignore
    import re

    book = epub.read_epub(str(path), options={"ignore_ncx": True})
    texts = []
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        html = item.get_content().decode("utf-8", errors="replace")
        clean = re.sub(r"<[^>]+>", " ", html)
        clean = re.sub(r"\s+", " ", clean).strip()
        if clean:
            texts.append(clean)
    return "\n\n".join(texts)


# ── Utility ───────────────────────────────────────────────────────────────────

def supported_extensions() -> list[str]:
    return sorted(SUPPORTED)
