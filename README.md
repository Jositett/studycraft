# 📖 StudyCraft

> **Craft structured, research-backed practice guides from any document.**
> Upload a PDF, DOCX, TXT, RTF, or Markdown file — StudyCraft auto-detects every chapter and subchapter, enriches each with live web research, and generates a complete study guide exportable to Markdown, HTML, and PDF.

---

## Features

- **Any subject, any document** — not tied to any topic or file format
- **Auto chapter + subchapter detection** — numbered headings, ALL-CAPS headers, or fixed-window fallback
- **RAG grounding** — indexes your document into a local vector store so the LLM stays on-topic
- **Live web research** — DuckDuckGo searches per chapter for current best practices and examples
- **Crash recovery** — per-chapter cache; `--resume-from 5` skips chapters already generated
- **Three export formats** — `.md` (edit-friendly), `.html` (shareable), `.pdf` (print-ready)
- **CLI + Web UI** — terminal or browser interface

---

## Quick Start

```bash
# 1. Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Set up project
cd studycraft && uv sync

# 3. Configure API key
cp .env.example .env   # then edit .env with your OpenRouter key

# 4. Generate
uv run studycraft generate "your_document.pdf"
```

---

## CLI Commands

```bash
uv run studycraft generate "textbook.pdf"                    # Full guide
uv run studycraft generate "notes.pdf" --subject "Calculus"  # Override subject
uv run studycraft generate "doc.pdf" --chapter 3             # Single chapter
uv run studycraft generate "doc.pdf" --resume-from 5         # Resume after crash
uv run studycraft inspect  "doc.pdf"                         # Preview outline only
uv run studycraft export   "output/guide.md"                 # Re-export to HTML/PDF
uv run studycraft models                                      # List recommended models
```

---

## Supported Files

PDF · DOCX · TXT · MD · RTF

---

## Web UI

```bash
uv add fastapi uvicorn python-multipart
uv run studycraft-web
# Open http://localhost:8000
```

---

## Output

```
output/
├── <Subject>_Practice_Guide.md
├── <Subject>_Practice_Guide.html
├── <Subject>_Practice_Guide.pdf
└── .cache/ch01.md … chN.md    ← crash recovery cache
```

See `PLAN.md` for the full development roadmap.
