# AGENTS.md — StudyCraft Engineering Guide

> **This file is the single source of truth for any AI agent or engineer working in this codebase.**
> Read it fully before writing a single line of code. When in doubt, re-read it and ask.

---

## 1. Project Overview

**StudyCraft** is a Python-based tool for generating structured study practice guides from documents, with RAG-enhanced content, web research integration, multi-format export, audio/video guide generation, and a web UI. It supports local generation with LLMs via OpenRouter and is distributable via Docker.

**What it does:**
- Load documents (PDF, DOCX, TXT, MD, RTF, EPUB) and auto-detect chapters
- RAG (Retrieval-Augmented Generation) using ChromaDB + sentence-transformers for context-aware generation
- Per-chapter web research via DuckDuckGo (6h cache, per-query timeout) to supplement content
- Generate practice guides with 8 sections: learning objectives, key concepts, worked examples, quizzes, answer keys
- Export to Markdown, HTML, PDF (Playwright), DOCX, EPUB with 9 customizable themes and TOC navigation
- **Generate audio guides** using multiple TTS engines (Chatterbox, KittenTTS, Coqui/XTTS-v2, OpenRouter)
- **Generate video guides** using OpenRouter's video generation API (free models only)
- Persistent job tracking via SQLite-backed job store
- Web UI (FastAPI + Jinja2, SSE streaming, BYOK) and CLI interface
- Docker support for self-hosting

**Stack:**
- Language: Python 3.12+
- Package management: uv (CPU-only torch override via `[tool.uv]`)
- CLI: `src/studycraft/cli.py` (Typer)
- Web UI: FastAPI + Jinja2 (`src/studycraft/web.py` + `templates/index.html`)
- RAG: ChromaDB + sentence-transformers (`all-MiniLM-L6-v2`)
- LLM Integration: OpenRouter API (`model_registry.py`, cached to `~/.studycraft/models.json`)
- TTS Engines: Chatterbox (MIT), KittenTTS (Apache 2.0), Coqui/XTTS-v2 (MPL 2.0), OpenRouter (free only)
- Video: OpenRouter video API (async) + videopython/ffmpeg composer
- Export: Playwright (PDF), python-docx (DOCX), ebooklib (EPUB)
- Job Storage: SQLite (`jobstore.py`)
- CI: `scripts/ci.py`, `scripts/release.py`, `scripts/deploy.py`
- Containerization: Docker, docker-compose

---

## 2. Runtime — uv Only

**This is a uv project. Never use `pip`, `pip3`, or `python -m pip`.**

```bash
uv sync                          # Core install (no TTS, no PDF, no video)
uv sync --extra pdf              # Add PDF export (Playwright/Chromium)
uv sync --extra tts-kitten       # Add KittenTTS (lightweight, CPU-only)
uv sync --extra tts-chatterbox   # Add Chatterbox (multilingual, MIT)
uv sync --extra tts-coqui        # Add Coqui/XTTS-v2 (1100+ langs)
uv sync --extra tts              # Add all TTS engines
uv sync --extra video            # Add video generation (videopython)
uv run studycraft-web            # Launch web UI
```

If `uv sync` unexpectedly removes packages, use `--frozen` to reinstall from the lockfile without re-resolving:
```bash
uv sync --frozen
```

Windows (PowerShell 7) — set UTF-8 before generation:
```powershell
$env:PYTHONIOENCODING = "utf-8"; $env:PYTHONUTF8 = "1"
uv run studycraft generate "doc.pdf"
```

---

## 3. Core Commands

### Generation
```bash
studycraft generate <file> [OPTIONS]

-o, --output PATH           Output directory
-d, --difficulty TEXT       beginner | intermediate | advanced  [default: intermediate]
-t, --theme TEXT            dark | light | nord | solarized | dracula | github | monokai | ocean | rose-pine
-w, --workers INT           Parallel chapter workers  [default: 1]
-x, --context PATH          Extra context files (RAG), repeatable
-c, --chapter INT           Generate single chapter only
-r, --resume-from INT       Resume from chapter N (uses cache)
-s, --subject TEXT          Override subject name
-m, --model TEXT            OpenRouter model ID override
--with-answers              Generate answer key
--with-audio                Generate audio guide (requires tts extra)
--tts-engine TEXT           kitten | chatterbox | coqui | openrouter
--tts-voice TEXT            Voice name (engine-specific)
--tts-speed FLOAT           Playback speed multiplier  [default: 1.0]
--with-video                Generate video guide (requires video extra)
--clear-cache               Delete cached chapters before generating
--rate-limit INT            Seconds between chapters  [default: 5]
```

### Audio Generation (Standalone)
```bash
studycraft generate-audio <guide.md> [OPTIONS]
  --tts-engine TEXT    kitten | chatterbox | coqui | openrouter
  --tts-voice TEXT     Voice name (engine-specific)
  --tts-speed FLOAT    Playback speed  [default: 1.0]
  -o, --output PATH    Output directory  [default: output/audio/]
```

### Video Generation (Standalone)
```bash
studycraft generate-video <guide.md> [OPTIONS]
  --video-model TEXT        OpenRouter video model ID
  --video-resolution TEXT   e.g. 1080p
  -o, --output PATH         Output directory  [default: output/videos/]
```

### Other CLI Commands
```bash
studycraft validate <guide.md>       # Validate guide output
studycraft inspect <file> [--rag]    # Inspect chapters / RAG chunks
studycraft models                    # List available OpenRouter models
studycraft gist <guide.md>           # Publish guide as a GitHub Gist (requires GITHUB_TOKEN)
```

### CI & Release
```bash
uv run python scripts/ci.py              # Full CI: lint + test + build
uv run python scripts/ci.py --lint       # Lint only
uv run python scripts/ci.py --test       # Test only
uv run python scripts/release.py 0.9.3   # CI + bump version + tag + build
```

### Deployment
```bash
# HuggingFace Spaces
uv run python scripts/deploy.py --target huggingface --setup    # Create Space (one-time)
uv run python scripts/deploy.py --target huggingface --deploy   # Push code to Space
uv run python scripts/deploy.py --target huggingface --secret   # Set OPENROUTER_API_KEY

# Local Docker
uv run python scripts/deploy.py --target local         # Build & run in background
uv run python scripts/deploy.py --target local --stop  # Stop container
```

---

## 4. Key File Map

| Purpose | Path |
|---------|------|
| CLI entry point | `src/studycraft/cli.py` — do not modify without testing all CLI commands |
| Orchestration engine | `src/studycraft/engine.py` — load → detect → RAG → research → generate → export |
| Document loader | `src/studycraft/loader.py` — PDF, DOCX, TXT, MD, RTF, EPUB |
| Chapter detector | `src/studycraft/detector.py` — numbered, Roman numeral, ALL-CAPS, LLM fallback |
| RAG integration | `src/studycraft/rag.py` — ChromaDB + sentence-transformers, chunk metadata |
| Web researcher | `src/studycraft/researcher.py` — DuckDuckGo per chapter, 6h cache |
| Guide template | `src/studycraft/template.py` — universal 8-section practice guide |
| Guide validator | `src/studycraft/validator.py` — checks sections, examples, quiz, placeholders |
| Theme manager | `src/studycraft/themes.py` — 9 themes (dark, light, nord, solarized, dracula, github, monokai, ocean, rose-pine) |
| TTS engines | `src/studycraft/tts_engines.py` — Chatterbox, KittenTTS, Coqui/XTTS-v2, OpenRouter |
| Audio generator | `src/studycraft/audio_generator.py` — orchestrates TTS with dependency injection |
| Video generator | `src/studycraft/video_generator.py` — OpenRouter video API (free models only, async) |
| Video composer | `src/studycraft/video_composer.py` — combines video + audio + text overlays |
| Export (MD/HTML/PDF) | `src/studycraft/export.py` |
| Export DOCX | `src/studycraft/export_docx.py` |
| Export EPUB | `src/studycraft/export_epub.py` |
| Model registry | `src/studycraft/model_registry.py` — fetches from OpenRouter API, caches to `~/.studycraft/models.json`, retries 3× |
| Job store | `src/studycraft/jobstore.py` — SQLite-backed persistent job tracking, SQL injection prevention |
| Web UI | `src/studycraft/web.py` — FastAPI + SSE streaming + auth |
| Web UI template | `src/studycraft/templates/index.html` — Jinja2, autoescape |
| CI script | `scripts/ci.py` |
| Release script | `scripts/release.py` — bumps version in pyproject.toml, `__init__.py`, web.py |
| Deploy script | `scripts/deploy.py` — HuggingFace Spaces & local Docker Compose |
| Env config | `.env` — git-ignored; set `OPENROUTER_API_KEY` |
| Output directory | `output/` — generated guides, exports |
| Audio output | `output/audio/` — generated audio files (MP3) |
| Video output | `output/videos/` — generated video files |
| Chapter cache | `.cache/` — per-chapter markdown cache for crash recovery |

---

## 5. Architecture Principles

### 5.1 uv-First Dependency Management
All dependency operations use `uv`. Never use `pip` or `python -m pip`.
```bash
uv add <package>          # Add new dependency
uv remove <package>       # Remove dependency
uv sync                   # Sync environment with pyproject.toml
uv sync --frozen          # Reinstall from lockfile without re-resolving
```

### 5.2 Engine Orchestration Flow
All generation workflows follow the sequence in `engine.py`:
1. Load document via `loader.py`
2. Detect chapters via `detector.py` (regex → LLM fallback → fixed-window)
3. Index content in ChromaDB via `rag.py`
4. Run per-chapter web research via `researcher.py`
5. Generate guide content using OpenRouter LLMs
6. Validate output via `validator.py` (auto-retry once on failure)
7. Export to all formats via `export*.py`
8. Optionally generate audio via `audio_generator.py`
9. Optionally generate video via `video_generator.py` + `video_composer.py`

Do not modify this flow without updating `engine.py` and testing end-to-end generation.

### 5.3 RAG Context Rules
- RAG chunks are stored with metadata (chapter, page number, source file)
- Cached RAG indexes are per-source document; re-index only when source document changes
- Chunk IDs are sanitized: `re.sub(r"[^\w-]", "_", source_name)`
- Use `--clear-cache` to force re-indexing

### 5.4 Export Theme Consistency
All export formats (MD, HTML, PDF, DOCX, EPUB) must support all 9 themes defined in `themes.py`:
- Theme logic lives exclusively in `themes.py`
- Never hardcode theme-specific styles in export modules
- Test theme output across all formats when modifying `themes.py`

### 5.5 Job Persistence
All generation jobs are tracked in the SQLite job store (`jobstore.py`):
- `JobStore` is a module-level singleton in `web.py` (startup/shutdown lifecycle)
- Status updates: `pending → in_progress → completed | failed | stopped`
- Failed jobs can be resumed via `--resume-from`
- `update()` validates column names against `_ALLOWED_COLS` to prevent SQL injection

### 5.6 TTS Audio Generation
Audio guides use dependency injection to support multiple TTS engines:

| Engine | License | Size | Notes |
|--------|---------|------|-------|
| KittenTTS | Apache 2.0 | 15–80M | Lightweight, CPU-only, 8 built-in voices |
| Chatterbox | MIT | 350–500M | Multilingual (23+ langs), voice cloning |
| Coqui/XTTS-v2 | MPL 2.0 | 1.7B | 1100+ languages, zero-shot voice cloning |
| OpenRouter TTS | Cloud | — | Free models only (verified via `model_registry.py`) |

Engine selection priority (configurable via `--tts-engine`):
1. KittenTTS (default, lightweight)
2. Chatterbox (quality + multilingual)
3. Coqui/XTTS-v2 (maximum language support)
4. OpenRouter (cloud fallback, free models only)

**Key rules:**
- OpenRouter TTS only uses models verified as free (`is_free=True` in `model_registry.py`)
- All engines injected via `TTSEngine` base class in `tts_engines.py`
- Audio generation is optional: enable with `--with-audio` flag

### 5.7 Video Generation
Video guides use OpenRouter's video generation API (asynchronous workflow):

- **OpenRouter Video API** — Free models only (verified via `model_registry.py`)
- **Workflow**: Submit job → Poll status → Download video
- **Supported models**: `google/veo-3.1`, `Seedance 2.0/1.5`, `Wan 2.7/2.6`, `Sora 2 Pro`
- **Video composition**: Combine generated video + TTS audio + text overlays via `video_composer.py` (videopython or ffmpeg fallback)

**Key rules:**
- Only free models are allowed (checked via `model_registry.py`)
- Video generation is asynchronous (polling with configurable interval)
- Video generation is optional: enable with `--with-video` flag

### 5.8 Web UI SSE Streaming
Progress updates use Server-Sent Events (not polling):
- Endpoint: `GET /api/stream/{job_id}` — streams JSON job state every 1s
- Frontend uses `EventSource("/api/stream/{jobId}")` 
- Stream closes when status is `done`, `error`, or `stopped`

---

## 6. Security Rules

### Secrets
- Set `OPENROUTER_API_KEY` in `.env` (git-ignored)
- `STUDYCRAFT_WEB_TOKEN` enables bearer token auth on all generation endpoints
- Never commit secrets to source code, `.env.example`, or any tracked files

### Input Sanitization
- Document loader validates file extensions and sizes before processing
- RAG chunk IDs sanitized with `re.sub(r"[^\w-]", "_", source_name)`
- `JobStore.update()` validates column names against `_ALLOWED_COLS`
- User-provided CLI arguments (difficulty, theme) validated against allowed values

### Model Usage
- Only use OpenRouter models registered in `model_registry.py`
- Never hardcode model IDs in generation logic
- Free model tiers are default; specify paid models explicitly via `-m`
- OpenRouter TTS and video only use models where `is_free=True`

---

## 7. Data Persistence

| Store | Location | Notes |
|-------|----------|-------|
| Job store | `output/jobs.db` | SQLite, module-level singleton |
| Chapter cache | `.cache/` | Per-chapter markdown; clear with `--clear-cache` |
| RAG index | `rag_index/` | ChromaDB; re-indexed when source changes |
| Model health cache | `~/.studycraft/model_health.json` | 6h TTL |
| Research cache | `~/.studycraft/research_cache.json` | 6h TTL |
| Model list cache | `~/.studycraft/models.json` | Refreshed via `/api/models?refresh=1` |

Never commit `.cache/`, `rag_index/`, `output/`, or `uploads/` to the repository.

---

## 8. Testing

```bash
uv run python scripts/ci.py --test    # Run all tests
pytest tests/test_engine.py -v        # Run specific test file
```

Tests follow `tests/test_*.py` naming. All tests must pass before committing. Current count: **96 tests**.

Key test files:
- `tests/test_engine.py` — mocked LLM end-to-end pipeline
- `tests/test_web.py` — FastAPI test client (SSE, auth, status endpoints)
- `tests/test_loader.py` — document loading across all formats
- `tests/test_detector.py` — chapter detection strategies
- `tests/test_export.py` — export pipeline (MD, HTML, DOCX, EPUB)
- `tests/test_validator.py` — output validation checks
- `tests/test_themes.py` — theme system
- `tests/test_model_registry.py` — model fetching + cache
- `tests/test_jobstore.py` — SQLite job store

---

## 9. Code Style

- Follow PEP8; use existing codebase style as reference
- Type hints for all exported functions and class methods
- Explicit return types on all public functions
- Files: `snake_case.py` | Classes: `PascalCase` | Functions/variables: `snake_case` | Constants: `UPPER_SNAKE_CASE` | CLI options: `kebab-case`
- Imports order: stdlib → third-party → local studycraft modules
- `ruff` config: line-length 100, target py312 — run `uv run ruff check src/ --fix` before committing

---

## 10. External Services

All external service integrations use dedicated modules:
```python
from studycraft.model_registry import get_model       # OpenRouter LLM
from studycraft.researcher import search_web           # DuckDuckGo research
from studycraft.rag import get_rag_context             # ChromaDB RAG
from studycraft.tts_engines import get_tts_engine      # TTS
from studycraft.video_generator import generate_video  # OpenRouter video
```

Never call external APIs directly in route handlers or generation logic.

---

## 11. Definition of Done

A task is complete only when **all** of the following are true:

- [ ] `uv run python scripts/ci.py --lint` passes with zero errors
- [ ] `uv run python scripts/ci.py --test` passes (or failing tests explicitly skipped with documented reason)
- [ ] No secrets in source code or committed files
- [ ] `src/studycraft/` modules updated if new features are added
- [ ] `AGENTS.md` and CLI `--help` updated if new commands/options are added
- [ ] Generated output tested for all supported export formats if export logic changed
- [ ] TTS engine integration tested (kitten, chatterbox, coqui, openrouter fallback)
- [ ] Video generation tested (OpenRouter free models only)
- [ ] `.env.example` updated if new env vars are required
- [ ] Docker configuration updated if new dependencies or env vars are added
- [ ] `TASK_TRACKER.md` updated (move completed items, add new backlog items)

---

## 12. When You Are Unsure

**Stop and ask before proceeding.** Specifically, ask before:
- Modifying `engine.py`, `loader.py`, or `detector.py` core logic
- Changing OpenRouter API integration or adding new LLM providers
- Modifying RAG embedding models or ChromaDB schema
- Adding new Python dependencies (`uv add <package>` — update `pyproject.toml`)
- Changing export logic for existing formats (PDF, DOCX, EPUB)
- Modifying Docker configuration or CI scripts
- Running destructive operations on cached or output files

---

## 13. Root Hygiene

| What | Where |
|------|-------|
| Generated guides, exports | `output/` |
| Audio output | `output/audio/` |
| Video output | `output/videos/` |
| Chapter cache, RAG indexes | `.cache/`, `rag_index/` |
| CI logs, test outputs | `output/logs/` |
| Debug helper scripts | `scripts/debug/` |
| Agent task prompts | `tasks/agent-prompts/` |

Do not leave scratch files, temp PDFs, or ad-hoc exports in the project root.
