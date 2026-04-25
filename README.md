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

## Features

- **Universal document loader** — PDF, DOCX, TXT, RTF, EPUB, Markdown
- **Auto chapter detection** — Roman numerals, appendix/glossary filtering, LLM-assisted fallback
- **RAG pipeline** — ChromaDB + MiniLM embeddings, per-chapter context injection
- **Web research** — DuckDuckGo per chapter with 6h research cache
- **Multi-format export** — Markdown, HTML, PDF (Playwright), DOCX, EPUB
- **Theme system** — 9 built-in themes (dark, light, nord, solarized, dracula, github, monokai, ocean, rosé-pine)
- **Audio guides** — TTS via KittenTTS, Chatterbox, or Coqui/XTTS-v2 (optional extras)
- **Video guides** — OpenRouter-powered video generation (`--extra video`)
- **Difficulty levels** — `beginner`, `intermediate`, `advanced`
- **BYOK** — users supply their own OpenRouter API key in the browser
- **Web UI** — FastAPI + Jinja2, SSE streaming progress, pause/stop controls
- **CLI** — full Typer CLI with all options

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

## Installation

```bash
# Core only
uv sync

# With PDF export (Playwright)
uv sync --extra pdf
playwright install chromium

# With TTS
uv sync --extra tts-chatterbox   # or tts-kitten / tts-coqui / tts (all)

# With video generation
uv sync --extra video
```

## Docker

```bash
docker compose up
# → http://localhost:8000
```

## CLI Reference

```
studycraft generate <file> [OPTIONS]

Options:
  -o, --output PATH         Output directory
  -d, --difficulty TEXT     beginner | intermediate | advanced  [default: intermediate]
  -t, --theme TEXT          dark | light | nord | solarized | dracula | ...  [default: dark]
  -w, --workers INT         Parallel chapter workers  [default: 1]
  -x, --context PATH        Extra context files (RAG), repeatable
  --with-answers            Include answer key
  --with-audio              Generate audio guide (requires tts extra)
  --with-video              Generate video guide (requires video extra)
  --model TEXT              OpenRouter model ID override
```

## Environment Variables

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API key (required) |
| `STUDYCRAFT_WEB_TOKEN` | Optional bearer token for web UI auth |
| `HF_TOKEN` | HuggingFace token for private model downloads |

## Project Structure

```
src/studycraft/
├── cli.py            # Typer CLI
├── web.py            # FastAPI app + SSE streaming
├── engine.py         # Generation pipeline
├── detector.py       # Chapter detection
├── loader.py         # Document loaders
├── rag.py            # ChromaDB RAG
├── researcher.py     # DuckDuckGo research
├── export.py         # HTML/PDF/Markdown export
├── export_docx.py    # DOCX export
├── export_epub.py    # EPUB export
├── themes.py         # Theme system
├── model_registry.py # OpenRouter model registry
├── jobstore.py       # SQLite job store
├── validator.py      # Output validation
└── templates/
    └── index.html    # Web UI
```

## Development

```bash
uv sync
pytest                  # run all tests
ruff check src tests    # lint
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

## License

[Apache 2.0](LICENSE)
