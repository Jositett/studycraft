# StudyCraft

> **Craft structured, research-backed practice guides from any document.**
> Upload a PDF, DOCX, TXT, RTF, EPUB, or Markdown file -- StudyCraft auto-detects every chapter and subchapter, enriches each with live web research, and generates a complete study guide exportable to Markdown, HTML, PDF, DOCX, and EPUB.

---

## Features

- **Any subject, any document** -- not tied to any topic or file format
- **Auto chapter + subchapter detection** -- numbered headings, Roman numerals, ALL-CAPS headers, or fixed-window fallback
- **RAG grounding** -- indexes your document into a local vector store so the LLM stays on-topic
- **Live web research** -- DuckDuckGo searches per chapter for current best practices and examples
- **Output validation** -- checks sections, examples, quiz questions; auto-retries on failure
- **Answer key generation** -- `--with-answers` produces a separate answer key
- **Crash recovery** -- per-chapter cache; `--resume-from 5` skips chapters already generated
- **Parallel generation** -- `--workers N` for concurrent chapter generation
- **Five export formats** -- `.md`, `.html`, `.pdf`, `.docx`, `.epub`
- **Live model registry** -- fetches models from OpenRouter API with free/vision filters
- **CLI + Web UI** -- terminal or browser interface
- **Docker ready** -- single command to self-host

---

## Quick Start

### Option 1: Docker (recommended for self-hosting)

```bash
# 1. Clone and configure
git clone https://github.com/youruser/studycraft.git
cd studycraft
cp .env.example .env   # edit .env with your OpenRouter key

# 2. Run
docker compose up -d

# Open http://localhost:8000
```

### Option 2: Local with uv

```bash
# 1. Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Set up project
cd studycraft && uv sync

# 3. Configure API key
cp .env.example .env   # edit .env with your OpenRouter key

# 4. Generate
uv run studycraft generate "your_document.pdf"
```

### Option 3: Docker CLI

```bash
# Generate a guide using Docker directly
docker run --rm -v $(pwd):/app/uploads -v $(pwd)/output:/app/output \
  --env-file .env studycraft \
  studycraft generate /app/uploads/your_document.pdf
```

---

## CLI Commands

```bash
# Generation
studycraft generate "textbook.pdf"                          # Full guide
studycraft generate "notes.pdf" --subject "Calculus"        # Override subject
studycraft generate "doc.pdf" --chapter 3                   # Single chapter
studycraft generate "doc.pdf" --resume-from 5               # Resume after crash
studycraft generate "doc.pdf" --with-answers                # Include answer key
studycraft generate "doc.pdf" --workers 3                   # Parallel generation
studycraft generate "doc.pdf" --context "extra.pdf"         # Add RAG context files

# Inspection & validation
studycraft inspect  "doc.pdf"                               # Preview outline
studycraft inspect  "doc.pdf" --rag                         # Show RAG chunks per chapter
studycraft validate "output/guide.md"                       # Check guide quality

# Export & publish
studycraft export   "output/guide.md"                       # Re-export to all formats
studycraft gist     "output/guide.md"                       # Publish as GitHub Gist

# Models
studycraft models                                           # List all models
studycraft models --free --vision                           # Free vision-capable models
studycraft models --search "llama"                          # Search models
studycraft models --refresh                                 # Force refresh from API
```

---

## Supported Files

PDF, DOCX, TXT, MD, RTF, EPUB

---

## Web UI

The web UI is the default when you run `studycraft` with no arguments:

```bash
# Launches web UI at http://localhost:8000
uv run studycraft

# Or explicitly
uv run studycraft-web

# With Docker
docker compose up -d
```

---

## Output

```text
output/
├── <Subject>_Practice_Guide.md
├── <Subject>_Practice_Guide.html
├── <Subject>_Practice_Guide.pdf
├── <Subject>_Practice_Guide.docx
├── <Subject>_Practice_Guide.epub
├── <Subject>_Answer_Key.md          (with --with-answers)
└── .cache/ch01.md ... chN.md        (crash recovery cache)
```

---

## Environment Variables

| Variable | Required | Description |
|-----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | Get a free key at [OpenRouter](https://openrouter.ai) |
| `GITHUB_TOKEN` | No | For `studycraft gist` (gist scope) |

---

## Docker

```bash
# Build
docker build -t studycraft .

# Run web UI
docker run -p 8000:8000 --env-file .env studycraft

# Run with persistent storage
docker compose up -d

# Run CLI command
docker run --rm --env-file .env -v $(pwd)/output:/app/output studycraft \
  studycraft generate /app/uploads/doc.pdf
```

---

## Development

```bash
uv sync --group dev                    # Install with dev deps
uv run python scripts/ci.py            # Run full CI (lint + test + build)
uv run python scripts/ci.py --lint     # Lint only
uv run python scripts/ci.py --test     # Test only
uv run python scripts/ci.py --build    # Build only
uv run python scripts/release.py 0.7.0 # Release: CI + bump + tag + build
```

See `PLAN.md` for the full development roadmap and `CHANGELOG.md` for version history.
