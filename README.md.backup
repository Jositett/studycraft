# StudyCraft

> **AI-powered practice guides with audio narration and video presentations.**
> Upload any document (PDF, DOCX, TXT, RTF, EPUB, MD) and get a complete study guide with RAG-powered context, live web research, and export to multiple formats. Optional audio (TTS) and video generation.

---

## Features

- **Any subject, any document** -- PDF, DOCX, TXT, RTF, EPUB, MD -- auto-detects chapters
- **RAG grounding** -- ChromaDB vector store keeps LLM on-topic with your content
- **Live web research** -- DuckDuckGo searches per chapter for current best practices
- **Output validation** -- auto-retries if sections or quizzes are incomplete
- **Answer key generation** -- `--with-answers` produces solutions for all exercises
- **Crash recovery** -- per-chapter cache; resume with `--resume-from N`
- **Parallel generation** -- `--workers N` for concurrent chapter creation
- **Audio guides** -- `--with-audio` generates narrated versions using TTS engines:
  - KittenTTS (lightweight, CPU-only, 8 voices)
  - Chatterbox (high quality, multilingual, MIT)
  - Coqui/XTTS-v2 (1100+ languages)
- **Video guides** -- `--with-video` creates AI-generated presentations (OpenRouter models)
- **Nine export themes** -- `dark`, `light`, `nord`, `solarized`, `dracula`, `github`, `monokai`, `ocean`, `rose-pine`
- **Five export formats** -- `.md`, `.html`, `.pdf`, `.docx`, `.epub` with TOC
- **Live model registry** -- fetches OpenRouter models with free/vision filters
- **Web UI + CLI** -- FastAPI web interface and command-line tool
- **Docker-ready** -- self-host with `docker-compose` or deploy to HuggingFace Spaces

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
studycraft generate "doc.pdf" --theme dracula                # Choose export theme
studycraft generate "doc.pdf" --difficulty beginner           # Set difficulty level
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
| `HF_TOKEN` | No | HuggingFace token for faster RAG model downloads. Get one at [HuggingFace](https://huggingface.co/settings/tokens) |
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

### HuggingFace Spaces

Deploy StudyCraft as a public or private Space on HuggingFace:

```bash
# One-time: create the Space
uv run python scripts/deploy.py --target huggingface --setup --org YOUR_USERNAME

# Deploy code (updates the Space)
uv run python scripts/deploy.py --target huggingface --deploy

# Set your OpenRouter API key as a secret (required)
uv run python scripts/deploy.py --target huggingface --secret
```

The deploy script:
- Creates an `hf-deploy` branch with the correct `README.md` (YAML frontmatter)
- Pushes to HuggingFace Spaces (Docker SDK)
- Uses `cpu-basic` hardware by default (free tier)

**Note:** The Dockerfile installs Playwright with `--extra pdf` to enable PDF export.
Set `OPENROUTER_API_KEY` in Space secrets to enable LLM generation.

---

## Development

```bash
uv sync --group dev                    # Install with dev deps
uv run python scripts/ci.py            # Run full CI (lint + test + build)
uv run python scripts/ci.py --lint     # Lint only
uv run python scripts/ci.py --test     # Test only
uv run python scripts/ci.py --build    # Build only
uv run python scripts/release.py 0.9.0 # Release: CI + bump + tag + build
```

### Dependency Management

**Important:** This project uses `uv` for all dependency operations. Never use `pip` directly inside the virtual environment.

- **Add a new dependency**: `uv add <package>`
- **Update all dependencies**: `uv sync` (resolves and updates `uv.lock`)
- **Reinstall without re-resolving** (safe when lockfile is trusted): `uv sync --frozen`
- **Install optional PDF support**: `uv sync --extra pdf`

If `uv sync` unexpectedly removes packages, it's because the lockfile is out of sync with `pyproject.toml`. Use `uv sync --frozen` to reinstall exactly what's locked, then run `uv add` to properly update dependencies.

### Windows Setup

Windows users should set UTF-8 encoding globally to avoid text corruption:

```powershell
# Set UTF-8 globally (add to your PowerShell profile)
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# Install dependencies (CPU-only, no CUDA)
uv sync

# If packages are missing after sync, reinstall from lockfile:
uv sync --frozen

# Install PDF export support (one-time, installs Chromium)
uv run studycraft setup-pdf
```

See `PLAN.md` for the full development roadmap and `CHANGELOG.md` for version history.
