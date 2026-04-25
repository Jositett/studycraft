# AGENTS.md — StudyCraft Engineering Guide

> **This file is the single source of truth for any AI agent or engineer working in this codebase.**
> Read it fully before writing a single line of code. When in doubt, re-read it and ask.

---

## 1. Project Overview

**StudyCraft** is a Python-based tool for generating structured study practice guides from documents, with RAG-enhanced content, web research integration, multi-format export, and a web UI. It supports local generation with LLMs via OpenRouter, and is distributable via Docker.

**What it does:**
- Load documents (PDF, DOCX, TXT, MD, RTF, EPUB) and auto-detect chapters
- RAG (Retrieval-Augmented Generation) using ChromaDB + sentence-transformers for context-aware generation
- Per-chapter web research via DuckDuckGo to supplement content
- Generate practice guides with sections, examples, quizzes, and answer keys
- Export to Markdown, HTML, PDF, DOCX, EPUB with 9 customizable themes
- **Generate audio guides** using multiple TTS engines (Chatterbox, KittenTTS, Coqui/XTTS-v2, OpenRouter)
- **Generate video guides** using OpenRouter's video generation API (free models only)
- Persistent job tracking via SQLite-backed job store
- Web UI (FastAPI) and CLI interface
- Docker support for self-hosting

**Stack:**
- Language: Python 3.12+
- Package management: uv
- CLI: `src/studycraft/cli.py` (entry point)
- Web UI: FastAPI + inline HTML (`src/studycraft/web.py`)
- RAG: ChromaDB + sentence-transformers
- LLM Integration: OpenRouter API (`model_registry.py`, cached to `~/.studycraft/models.json`)
- TTS Engines: **Chatterbox** (MIT, multilingual), **KittenTTS** (Apache 2.0, lightweight), **Coqui/XTTS-v2** (MPL 2.0, 1100+ langs), **OpenRouter** (cloud, free models only)
- Export: WeasyPrint (PDF), python-docx (DOCX), EPUB3 libraries
- Job Storage: SQLite (`jobstore.py`)
- CI: Custom `scripts/ci.py`, `scripts/release.py`
- Containerization: Docker, docker-compose

---

## 2. Runtime — uv Only

**This is a uv project. Never use `pip`, `pip3`, or `python -m pip`.**

```bash
uv sync                                  # Core install (no TTS, no PDF)
uv sync --extra pdf                      # Install with PDF support (playwright)
uv sync --extra tts-kitten               # Install KittenTTS for audio generation
uv sync --extra tts                      # Install all TTS engines (kitten + chatterbox + coqui)
uv run studycraft                        # Launch web UI (default)
```

Windows (PowerShell 7) note: Set UTF-8 encoding first for generation:
```powershell
$env:PYTHONIOENCODING="utf-8"; uv run studycraft generate "doc.pdf"
```

---

## 3. Core Commands

### Generation Options
```bash
# Generation options
-c, --chapter 3          # Generate single chapter
-r, --resume-from 5      # Resume from chapter (uses cache)
-s, --subject "Math"     # Override subject name
-m, --model <id>         # Specify OpenRouter model (default: openrouter/free)
-x, --context "extra.pdf" # Add supplementary RAG context files
-w, --workers 3          # Parallel generation
-d, --difficulty "beginner" # Difficulty (beginner, intermediate, advanced)
-t, --theme "dracula"     # Export theme (dark, light, nord, solarized, dracula, github, monokai, ocean, rose-pine)
--with-answers           # Generate answer key
--with-audio             # Generate audio guide using TTS
--tts-engine "kitten"    # TTS engine: kitten, chatterbox, coqui, openrouter
--tts-voice "Bella"      # Voice name (engine-specific)
--tts-speed 1.0          # Playback speed multiplier
--clear-cache            # Delete cached chapters
--rate-limit 5           # Seconds between chapters (default: 5)
```

### Audio Generation (Standalone)
```bash
# Generate audio from existing markdown guide
uv run studycraft generate-audio "guide.md"
uv run studycraft generate-audio "guide.md" --tts-engine chatterbox --tts-voice default
uv run studycraft generate-audio "guide.md" -o output/audio/

# Install TTS dependencies (as needed)
uv add --optional tts-kitten       # KittenTTS (lightweight, CPU-only)
uv add --optional tts-chatterbox   # Chatterbox (multilingual, MIT)
uv add --optional tts-coqui        # Coqui/XTTS-v2 (1100+ langs)
uv add --optional tts              # All TTS engines
```

### Video Generation (Standalone)
```bash
# Generate video from existing markdown guide
uv run studycraft generate-video "guide.md"
uv run studycraft generate-video "guide.md" --video-model google/veo-3.1 --video-resolution 1080p
uv run studycraft generate-video "guide.md" -o output/videos/

# Install video dependencies
uv add --optional video           # videopython for video composition
```

### CI & Release
```bash
uv run python scripts/ci.py              # Full CI: lint + test + build
uv run python scripts/ci.py --lint       # Lint only
uv run python scripts/ci.py --test       # Test only
uv run python scripts/release.py 0.9.0   # CI + bump version + tag + build
```

### Deployment
```bash
# HuggingFace Spaces
uv run python scripts/deploy.py --target huggingface --setup      # Create Space (one-time)
uv run python scripts/deploy.py --target huggingface --deploy    # Push code to Space
uv run python scripts/deploy.py --target huggingface --secret    # Set OPENROUTER_API_KEY

# Local Docker (docker-compose)
uv run python scripts/deploy.py --target local                    # Build & run in background
uv run python scripts/deploy.py --target local --stop            # Stop container
```

### Docker (manual)
```bash
docker compose up -d                     # Self-host web UI
docker run -p 8000:8000 --env-file .env studycraft  # Quick run
```

---

## 4. Key File Map

| Purpose | Path |
|---------|------|
| CLI entry point | `src/studycraft/cli.py` — **do not modify without testing all CLI commands** |
| Orchestration engine | `src/studycraft/engine.py` — load -> detect -> RAG -> research -> generate -> export |
| Document loader | `src/studycraft/loader.py` — PDF, DOCX, TXT, MD, RTF, EPUB |
| Chapter detector | `src/studycraft/detector.py` — numbered, Roman numeral, ALL-CAPS, fixed-window fallback |
| RAG integration | `src/studycraft/rag.py` — ChromaDB + sentence-transformers with chunk metadata |
| Web researcher | `src/studycraft/researcher.py` — DuckDuckGo per chapter |
| Guide validator | `src/studycraft/validator.py` — checks sections, examples, quiz, placeholders |
| Theme manager | `src/studycraft/themes.py` — 9 themes (dark, light, nord, solarized, dracula, github, monokai, ocean, rose-pine) |
| TTS engines | `src/studycraft/tts_engines.py` — Chatterbox, KittenTTS, Coqui/XTTS-v2, OpenRouter |
| Audio generator | `src/studycraft/audio_generator.py` — orchestrates TTS with dependency injection |
| Video generator | `src/studycraft/video_generator.py` — OpenRouter video API (free models only) |
| Video composer | `src/studycraft/video_composer.py` — combines video + audio + text overlays |
| Export (MD/HTML/PDF) | `src/studycraft/export.py` |
| Export DOCX | `src/studycraft/export_docx.py` |
| Export EPUB | `src/studycraft/export_epub.py` |
| Model registry | `src/studycraft/model_registry.py` — fetches from OpenRouter API, caches to `~/.studycraft/models.json` |
| Job store | `src/studycraft/jobstore.py` — SQLite-backed persistent job tracking |
| Web UI | `src/studycraft/web.py` — FastAPI + inline HTML |
| CI script | `scripts/ci.py` |
| Release script | `scripts/release.py` |
| Deploy script | `scripts/deploy.py` — HuggingFace Spaces & local Docker Compose deployment |
| Env config | `.env` — git-ignored, set `OPENROUTER_API_KEY` or `STUDYCRAFT_API_KEY` |
| Output directory | `output/` — generated guides, exports |
| Audio output | `output/audio/` — generated audio files (MP3) |
| Cache directory | `.cache/` — per-chapter markdown cache for crash recovery |

---

## 5. Architecture Principles

### 5.1 uv-First Dependency Management
All dependency operations use `uv`. Never use `pip` or manual `python -m pip` commands.
```bash
uv add <package>          # Add new dependency
uv remove <package>       # Remove dependency
uv sync                   # Sync environment with pyproject.toml
```

### 5.2 Engine Orchestration Flow
All generation workflows follow the sequence defined in `engine.py`:
1. Load document via `loader.py`
2. Detect chapters via `detector.py`
3. Index content in ChromaDB via `rag.py`
4. Run per-chapter web research via `researcher.py`
5. Generate guide content using OpenRouter LLMs
6. Validate output via `validator.py`
7. Export to all formats via `export*.py`

Do not modify this flow without updating `engine.py` and testing end-to-end generation.

### 5.3 RAG Context Rules
- RAG chunks are stored with metadata (chapter, page number, source file)
- Cached RAG indexes are per-source document; re-index only when source document changes
- Use `--clear-cache` to force re-indexing of all documents

### 5.4 Export Theme Consistency
All export formats (MD, HTML, PDF, DOCX, EPUB) must support all 9 themes defined in `themes.py`:
- Theme logic lives exclusively in `themes.py`
- Never hardcode theme-specific styles in export modules
- Test theme output across all formats when modifying `themes.py`

### 5.5 Job Persistence
All generation jobs are tracked in the SQLite job store (`jobstore.py`):
- Jobs are created when generation starts
- Status updates (pending, in_progress, completed, failed) are persisted
- Failed jobs can be resumed via `--resume-from` flag

### 5.6 TTS Audio Generation
Audio guides use dependency injection to support multiple TTS engines:

- **KittenTTS** (Apache 2.0, 15M-80M params) — Lightweight, CPU-only, 8 built-in voices
- **Chatterbox** (MIT, 350M-500M) — Multilingual (23+ langs), voice cloning, MIT license
- **Coqui/XTTS-v2** (MPL 2.0, 1.7B) — 1100+ languages, zero-shot voice cloning
- **OpenRouter TTS** — Cloud-based, ONLY for free models (checks `model_registry.py`)

Engine selection priority (configurable via `--tts-engine`):
1. KittenTTS (default, lightweight)
2. Chatterbox (quality + multilingual)
3. Coqui/XTTS-v2 (maximum language support)
4. OpenRouter (cloud fallback, free models only)

**Key rules:**
- OpenRouter TTS only uses models verified as free (`is_free=True` in `model_registry.py`)
- Python engines are preferred; OpenRouter is last-resort fallback
- All engines injected via `TTSEngine` base class in `tts_engines.py`
- Audio generation is optional: enable with `--with-audio` flag

### 5.7 Video Generation
Video guides use OpenRouter's video generation API (asynchronous workflow):

- **OpenRouter Video API** — Free models only (verified via `model_registry.py`)
- **Workflow**: Submit job → Poll status → Download video
- **Supported models**: `google/veo-3.1`, `Seedance 2.0/1.5`, `Wan 2.7/2.6`, `Sora 2 Pro`
- **Video composition**: Combine generated video + TTS audio + text overlays via `video_composer.py`

**Key rules:**
- Only free models are allowed (checked via `model_registry.py`)
- Video generation is asynchronous (polling with configurable interval)
- Video composer uses `videopython` (if available) or `ffmpeg` fallback
- Video generation is optional: enable with `--with-video` flag

---

## 6. Security Rules

### Secrets
- Set `OPENROUTER_API_KEY` or `STUDYCRAFT_API_KEY` in `.env` (git-ignored)
- Never commit secrets to source code, `.env.example`, or any tracked files
- The `.env` file is for local dev only; Docker uses `--env-file .env`

### Input Sanitization
- Document loader (`loader.py`) handles untrusted files; validate file extensions and sizes before processing
- RAG queries and web research inputs are sanitized to prevent injection attacks
- User-provided CLI arguments (subject, difficulty, theme) are validated against allowed values

### Model Usage
- Only use OpenRouter models as registered in `model_registry.py`
- Never hardcode model IDs in generation logic; use `model_registry.py` to fetch available models
- Free model tiers are default; specify paid models explicitly via `-m` flag

---

## 7. Data Persistence Changes

When modifying data storage components:

1. **Job Store (SQLite):**
   - Update `jobstore.py` schema definitions
   - Migrate existing SQLite databases if schema changes are breaking

2. **ChromaDB (RAG):**
   - Update `rag.py` collection schema for chunk metadata changes
   - Re-index all source documents after schema changes

3. **Cache:**
   - `.cache/` directory stores per-chapter markdown; clear with `--clear-cache`
   - Never commit cached files to the repository (add to `.gitignore`)

---

## 8. Testing

### Infrastructure
Tests are run via the CI script:
```bash
uv run python scripts/ci.py --test       # Run all tests
```

Add new tests for all features following existing test patterns. Test files follow `tests/test_*.py` naming conventions.

### Test Prompts
For AI-generated tests, use structured prompts in `tasks/agent-prompts/test-prompts/` (create this directory if needed).

---

## 9. Code Style

### Python
- Follow PEP8 conventions, use existing codebase style as reference
- Type hints for all exported functions and class methods
- Avoid `object` for unknown types; use `Optional`/`Union` with proper type guards
- Explicit return types on all public functions

### Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- CLI options: `kebab-case` (e.g., `--clear-cache`)

### Imports
Order: stdlib -> third-party -> local studycraft modules (`src/studycraft/*`)

### Comments
Write self-documenting code. Add comments only to explain non-obvious *why* logic, not *what*.

---

## 10. External Services

All external service integrations use dedicated modules:
```python
# OpenRouter LLM
from src.studycraft.model_registry import get_model

# Web research
from src.studycraft.researcher import search_web

# RAG
from src.studycraft.rag import get_rag_context
```

Never call external APIs directly in route handlers or generation logic; use the dedicated modules above.

---

## 11. Definition of Done

A task is complete only when **all** of the following are true:

- [ ] Code uses `uv run` for all Python executions, no `pip` or `python` direct calls
- [ ] `uv run python scripts/ci.py --lint` passes with zero errors
- [ ] `uv run python scripts/ci.py --test` passes (or failing tests are explicitly skipped with documented reason)
- [ ] No secrets in source code or committed files
- [ ] `src/studycraft/` modules updated if new features are added
- [ ] Documentation (AGENTS.md, CLI `--help`) updated if new commands/options are added
- [ ] Generated output tested for all supported export formats if export logic changed
- [ ] TTS engine integration tested (kitten, chatterbox, coqui, openrouter fallback)
- [ ] Audio output validated for all selected TTS engines
- [ ] Video generation tested (OpenRouter free models only)
- [ ] Video composer tested (videopython/ffmpeg fallback)
- [ ] `.env` example updated if new env vars are required
- [ ] Docker configuration updated if new dependencies or env vars are added

---

## 12. When You Are Unsure

**Stop and ask before proceeding.** This tool handles user documents and generated study materials.

Specifically, ask before:
- Modifying `engine.py`, `loader.py`, or `detector.py` core logic
- Changing OpenRouter API integration or adding new LLM providers
- Modifying RAG embedding models or ChromaDB schema
- Adding new Python dependencies (update `pyproject.toml` via `uv add`)
- Changing export logic for existing formats (PDF, DOCX, EPUB)
- Modifying Docker configuration or CI scripts
- Running destructive operations on cached or output files

The cost of asking is one message. The cost of a wrong assumption is corrupted user documents or broken generation.

---

## 13. Root Hygiene

Keep the project root clean:

| What | Where |
|------|-------|
| Generated guides, exports | `output/` |
| Chapter cache, RAG indexes | `.cache/` |
| CI logs, test outputs | `output/logs/`, `output/test-runs/` |
| Debug helper scripts | `scripts/debug/` |
| Archival notes | `docs/archive/` |
| Agent task prompts | `tasks/agent-prompts/` |

Do not leave scratch files, temp PDFs, or ad-hoc exports in the project root.
