---
title: StudyCraft
emoji: 📖
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 8000
pinned: false
suggested_hardware: cpu-upgrade
tags:
  - study-guides
  - education
  - audio
  - video
  - text-to-speech
  - rag
---

# StudyCraft 📖

Craft structured, research-backed practice guides from any document — PDF, DOCX, TXT, RTF, EPUB, or Markdown — powered by OpenRouter LLMs and ChromaDB RAG.

[![CI](https://github.com/Jositett/studycraft/actions/workflows/ci.yml/badge.svg)](https://github.com/Jositett/studycraft/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![HF Space](https://img.shields.io/badge/🤗%20Spaces-StudyCraft-indigo)](https://huggingface.co/spaces/Joedroid/studycraft)

---

## What It Does

StudyCraft takes any document and turns it into a fully structured practice guide — complete with learning objectives, key concepts, worked examples, quizzes, and an answer key. It auto-detects chapters, enriches each one with live web research and RAG context from your own files, then exports to every format you need.

---

## Features

### Core Pipeline

- **Universal document loader** — PDF, DOCX, TXT, RTF, EPUB, Markdown
- **Auto chapter detection** — numbered headings, Roman numerals, ALL-CAPS, appendix/glossary filtering, LLM-assisted TOC fallback
- **RAG pipeline** — ChromaDB + MiniLM embeddings, per-chapter context injection, chunk metadata (source, page, index)
- **Web research** — DuckDuckGo per chapter with 6h research cache and per-query timeout
- **Difficulty levels** — `beginner`, `intermediate`, `advanced` — controls example complexity, quiz depth, and language
- **Post-generation review** — auto-fixes unfilled `[...]` placeholders with a targeted LLM call
- **Auto model switching** — up to 5 fallbacks on persistent LLM failure, with 6h model health cache
- **Crash recovery** — per-chapter cache + `--resume-from` flag

### Export

- **Multi-format export** — Markdown, HTML, PDF (Playwright/Chromium), DOCX, EPUB
- **Theme system** — 9 built-in themes: `dark`, `light`, `nord`, `solarized`, `dracula`, `github`, `monokai`, `ocean`, `rosé-pine`
- **TOC navigation** — sticky sidebar (HTML), TOC page (PDF), anchor links (Markdown), Word TOC field (DOCX)
- **Answer key** — separate `Answer_Key.md` with quiz answers, exercise solutions, and mini-project guidance

### Audio Guides

Generate narrated audio from any guide using your choice of TTS engine:

| Engine | License | Size | Notes |
|--------|---------|------|-------|
| **KittenTTS** | Apache 2.0 | 15–80M | Lightweight, CPU-only, 8 built-in voices |
| **Chatterbox** | MIT | 350–500M | Multilingual (23+ langs), voice cloning |
| **Coqui/XTTS-v2** | MPL 2.0 | 1.7B | 1100+ languages, zero-shot voice cloning |
| **OpenRouter TTS** | Cloud | — | Free models only, cloud fallback |

### Video Guides

Generate video guides from any Markdown guide using OpenRouter's video generation API (free models only):

- Supported models: `google/veo-3.1`, `Seedance 2.0/1.5`, `Wan 2.7/2.6`, `Sora 2 Pro`
- Combines generated video + TTS audio + text overlays via `video_composer.py`
- Async workflow: submit → poll → download

### Web UI

- FastAPI + Jinja2, dark mode by default
- SSE streaming progress (real-time chapter updates, no polling)
- Pause/stop controls mid-generation
- Drag & drop context files (supplementary RAG)
- Dynamic model dropdown (live from OpenRouter API)
- BYOK — users supply their own OpenRouter API key in the browser
- Optional bearer token auth (`STUDYCRAFT_WEB_TOKEN`)

### CLI

- Full Typer CLI with Rich output and progress bars
- All generation, export, inspect, validate, and model commands
- `studycraft gist` — publish guide as a GitHub Gist

---

## Quick Start

```bash
# Install (CPU-only, recommended)
pip install uv
uv sync

# Set your OpenRouter API key
cp .env.example .env
# edit .env → OPENROUTER_API_KEY=sk-or-...

# Web UI
studycraft-web

# CLI
studycraft generate my-textbook.pdf --difficulty intermediate --theme dark
```

---

## Installation

```bash
# Core only
uv sync

# With PDF export (Playwright/Chromium)
uv sync --extra pdf
playwright install chromium

# With TTS audio generation
uv sync --extra tts-chatterbox   # Chatterbox (recommended)
uv sync --extra tts-kitten       # KittenTTS (lightweight)
uv sync --extra tts-coqui        # Coqui/XTTS-v2 (max language support)
uv sync --extra tts              # All TTS engines

# With video generation
uv sync --extra video
```

> **Windows note:** Set UTF-8 encoding before generating:
>
> ```powershell
> $env:PYTHONIOENCODING = "utf-8"; $env:PYTHONUTF8 = "1"
> ```
>
> If `uv sync` unexpectedly removes packages, use `uv sync --frozen` to reinstall from the lockfile.

---

## Docker

```bash
docker compose up
# → http://localhost:8000
```

---

## CLI Reference

```
studycraft generate <file> [OPTIONS]

Options:
  -o, --output PATH           Output directory
  -d, --difficulty TEXT       beginner | intermediate | advanced  [default: intermediate]
  -t, --theme TEXT            dark | light | nord | solarized | dracula | github | monokai | ocean | rose-pine  [default: dark]
  -w, --workers INT           Parallel chapter workers  [default: 1]
  -x, --context PATH          Extra context files (RAG), repeatable
  -c, --chapter INT           Generate a single chapter only
  -r, --resume-from INT       Resume from chapter N (uses cache)
  -s, --subject TEXT          Override subject name
  -m, --model TEXT            OpenRouter model ID override
  --with-answers              Include answer key
  --with-audio                Generate audio guide (requires tts extra)
  --tts-engine TEXT           kitten | chatterbox | coqui | openrouter
  --tts-voice TEXT            Voice name (engine-specific)
  --tts-speed FLOAT           Playback speed multiplier  [default: 1.0]
  --with-video                Generate video guide (requires video extra)
  --clear-cache               Delete cached chapters before generating
  --rate-limit INT            Seconds between chapters  [default: 5]

studycraft generate-audio <guide.md> [OPTIONS]   # Narrate an existing guide
studycraft generate-video <guide.md> [OPTIONS]   # Generate video from an existing guide
studycraft validate <guide.md>                   # Validate guide output
studycraft inspect <file> [--rag]                # Inspect chapters / RAG chunks
studycraft models                                # List available OpenRouter models
studycraft gist <guide.md>                       # Publish guide as a GitHub Gist
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API key (required) |
| `STUDYCRAFT_WEB_TOKEN` | Optional bearer token for web UI auth |
| `HF_TOKEN` | HuggingFace token for private model downloads |

---

## Project Structure

```
src/studycraft/
├── cli.py               # Typer CLI — all commands
├── web.py               # FastAPI app + SSE streaming
├── engine.py            # Generation pipeline orchestrator
├── detector.py          # Chapter detection (regex + LLM fallback)
├── loader.py            # Document loaders (PDF, DOCX, TXT, RTF, EPUB, MD)
├── rag.py               # ChromaDB RAG index
├── researcher.py        # DuckDuckGo research + 6h cache
├── template.py          # Universal 8-section practice guide template
├── validator.py         # Output validation (sections, examples, quiz, placeholders)
├── themes.py            # Theme system (9 themes, Theme dataclass)
├── export.py            # MD → HTML → PDF export with TOC + themes
├── export_docx.py       # DOCX export
├── export_epub.py       # EPUB export
├── tts_engines.py       # TTS engine adapters (Chatterbox, KittenTTS, Coqui, OpenRouter)
├── audio_generator.py   # Audio guide orchestrator
├── video_generator.py   # OpenRouter video generation (async)
├── video_composer.py    # Video + audio + text overlay composition
├── model_registry.py    # OpenRouter model fetcher + health cache
├── jobstore.py          # SQLite-backed persistent job tracking
└── templates/
    └── index.html       # Web UI (Jinja2)
```

---

## Development

```bash
uv sync
pytest                          # run all tests
ruff check src tests            # lint
python scripts/ci.py            # full CI: lint + test + build
python scripts/release.py 0.9.3 # bump version + tag + build
```

---

## Deployment

```bash
# HuggingFace Spaces
python scripts/deploy.py --target huggingface --setup    # create Space (one-time)
python scripts/deploy.py --target huggingface --deploy   # push code
python scripts/deploy.py --target huggingface --secret   # set API key

# Local Docker
python scripts/deploy.py --target local                  # build & run
python scripts/deploy.py --target local --stop           # stop
```

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

## License

[Apache 2.0](LICENSE)
