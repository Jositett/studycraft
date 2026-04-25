# Changelog

All notable changes to StudyCraft will be documented in this file.

## [0.9.1] — 2026-04-25

### Added
- SSE streaming endpoint `/api/stream/{job_id}` for real-time progress updates (replaces polling)
- API key authentication via `STUDYCRAFT_WEB_TOKEN` for secure deployments
- LLM-assisted TOC extraction fallback in `detector.py` (OpenRouter-powered chapter detection)
- Per-query research cache in `~/.studycraft/research_cache.json` (6h TTL, saves ~30s per run)
- Configurable 8s timeout per DuckDuckGo query
- Comprehensive test coverage: `tests/test_engine.py` (mocked LLM), `tests/test_web.py` (FastAPI client)

### Changed
- `pyproject.toml`: Added `[tool.uv]` config (CPU-only torch, reinstall-package), moved `playwright` to `pdf` optional extra, added `pytest-asyncio` and `httpx` to dev deps
- `JobStore` is now a module-level singleton with startup/shutdown lifecycle (prevents race conditions)
- Parallel worker loop now respects `on_check_control` for pause/stop
- RAG chunk IDs sanitized to valid characters (`re.sub(r"[^\w-]", "_", source_name)`)
- EPUB loader separates block vs inline tags to preserve paragraph structure
- Answer key generator caps sections before joining (avoids token overflow)
- `JobStore.update()` validates column names against allowed set (SQL injection prevention)
- Engine: extracted `_build_prompt()` method for testability
- Web UI: moved 800+ lines of inline HTML to `templates/index.html` using Jinja2 with autoescape
- Model registry: `fetch_models()` now retries 3× with 2s delay
- Developer experience: full `ruff` config (line-length 100, target py312), auto-formatted codebase
- Documentation: README now includes Windows setup and dependency management guidance; PLAN.md updated

### Fixed
- `uv sync` no longer unexpectedly removes packages (CPU-only torch override)
- `openai` dependency corrected to `>=1.82.0` (v2 does not exist on PyPI)
- Race condition in concurrent JobStore instantiation
- Lost pause/stop control in parallel generation mode
- Potential ChromaDB ID collisions from special characters in source filenames
- EPUB word concatenation due to aggressive tag stripping
- Answer key truncation bug (was slicing string instead of list)
- JobStore SQL injection vector via kwargs keys

### Development
- All 96 tests pass
- Ready for production use
- Added `scripts/deploy.py` for HuggingFace Spaces & Docker Compose deployment
- Dockerfile installs `--extra pdf` (Playwright) and sets writable dirs for UID 1000
- README.hf-spaces.md includes `hardware: cpu-basic` suggestion
- Updated frontend Usage Guide to document audio/video generation features

---

## [0.9.2] — 2026-04-25

### Added
- Comprehensive Usage Guide in frontend documenting:
  - Audio generation with KittenTTS, Chatterbox, Coqui/XTTS-v2
  - Video generation with OpenRouter video models
  - Theme selection, difficulty levels, and output formats
  - Optional dependency installation commands

### Changed
- Frontend template updated with clearer feature explanations
- Version bump to 0.9.2 across `pyproject.toml`, `__init__.py`, `web.py`

### Fixed
- Cross-platform file operations in `scripts/deploy.py` (Windows compatibility)
- HuggingFace CLI migration: `huggingface-cli` → `hf` in deploy script

---

## [0.9.1] — 2026-04-25

### Added
- Difficulty levels: `beginner`, `intermediate`, `advanced` — controls example complexity, quiz depth, and language
- `--difficulty` / `-d` CLI flag + web UI dropdown
- Post-generation review step — auto-fixes unfilled `[...]` placeholders with a targeted LLM call
- Auto model switching on persistent failure (up to 5 switches to verified fallback models)
- Model health testing: 1-token probe per free model, cached 6h at `~/.studycraft/model_health.json`
- `get_fallback_chain()`, `get_verified_free_models()`, `test_model()` in model registry
- `POST /api/models/test` endpoint to trigger health checks from web UI
- `/api/models` now prioritizes healthy models in dropdown
- Pause/stop controls in web UI progress card
- Context files drag & drop zone with file list and remove buttons
- `POST /api/control/{job_id}` endpoint for pause/stop/resume

### Changed
- Replaced `duckduckgo-search` with `ddgs` package (no more RuntimeWarning spam)
- PDF export strips emoji characters to prevent font encoding errors
- Engine fires progress callback after each chapter completes (not just before)
- Release script (`scripts/release.py`) now bumps version in all 3 files
- 53 tests passing

### Fixed
- PDF crash on emoji characters (`\U0001f4d6` in cover title)
- `NoneType` crash when LLM returns empty response
- 400 errors now trigger prompt truncation + retry
- Progress bar in web UI now updates between chapters

## [0.8.0] — 2025-01-21

### Added
- Theme system with 9 built-in themes: dark (default), light, nord, solarized, dracula, github, monokai, ocean, rosé-pine
- `themes.py` — `Theme` dataclass with 30+ color tokens, `get_theme()` / `list_themes()` API
- All export formats (HTML, PDF, DOCX, EPUB) now use theme-driven colors via dependency injection
- Table of Contents with navigation in all export formats:
  - HTML: sticky sidebar TOC with scroll-spy highlighting
  - PDF: cover page + TOC page with indented chapter listing
  - Markdown: TOC block with anchor links at top
  - DOCX: Word TOC field (auto-updates on open)
- `--theme` / `-t` CLI flag for generation and export
- Theme dropdown in web UI
- Themed code blocks, blockquotes, tables, headings, and cover across all formats

### Changed
- `export.py` — CSS now generated from theme instead of hardcoded; accepts `theme` param
- `export_docx.py` — heading/quote colors from theme
- `export_epub.py` — CSS generated from theme
- `engine.py` — `run()` accepts `theme` param, passes to export pipeline
- Dark mode default with proper contrast for HTML exports (cover, headings, code)
- 53 tests passing

## [0.7.0] — 2025-01-21

### Added
- EPUB file upload support (loader + web UI + CLI)
- Dark mode web UI by default with improved UX
- Dynamic model selection from OpenRouter API (replaces hardcoded list)
- Refresh models button with cache-busting (`/api/models?refresh=1`)
- Favicon (SVG book emoji) — no more 404
- Usage guide aside panel in web UI
- Custom scrollbar styling (dark theme)
- Progress time estimates in web UI ("~3m remaining")
- "Generate another" reset button after completion
- `HF_TOKEN` support in `.env` for authenticated HuggingFace downloads
- 429 rate-limit retry with exponential backoff in engine

### Changed
- Replaced `weasyprint` (requires GTK) with `fpdf2` (pure Python) for PDF export
- Fixed `researcher.py` import: `from ddgs import DDGS` → `from duckduckgo_search import DDGS`
- Web UI drop zone shows green border when file is selected
- Download buttons use flex grid layout with format-specific styling
- Answer key generation now uses same backoff retry logic
- 53 tests passing

### Removed
- `weasyprint` dependency (no longer requires GTK/native libs on Windows)

## [0.6.0] — 2025-01-20

### Added
- EPUB export via `export_epub.py` (ebooklib) -- auto-splits chapters, styled CSS, TOC navigation
- `studycraft gist` CLI command -- publish a Markdown guide as a GitHub Gist (requires `GITHUB_TOKEN`)
- GitHub Actions CI workflow (`.github/workflows/ci.yml`) -- lint + test on push/PR
- GitHub Actions release workflow (`.github/workflows/release.yml`) -- build + upload on tag push
- `ebooklib` added to project dependencies
- 1 new test: EPUB export verification (48 total)

### Changed
- `pyproject.toml` -- version bumped to 0.6.0
- `export.py` -- pipeline now produces `.epub` alongside `.md`, `.html`, `.pdf`, `.docx`

## [0.5.0] — 2025-01-20

### Added
- Richer RAG: chunk metadata (source, chunk_index), `query_detailed()`, `chunk_count()`
- `studycraft inspect --rag` flag -- indexes document and shows top RAG chunks per chapter
- DOCX export via `export_docx.py` -- automatically included in export pipeline
- Parallel chapter generation with `--workers N` / `-w N` flag (ThreadPoolExecutor)

### Changed
- `rag.py` -- metadatas now include `chunk_index`; new `query_detailed()` and `chunk_count()` methods
- `engine.py` -- refactored generation into `_generate_all()` supporting sequential and parallel modes
- `export.py` -- pipeline now produces `.docx` alongside `.md`, `.html`, `.pdf`
- `cli.py` -- added `--workers` flag to `generate`, `--rag` flag to `inspect`

## [0.4.0] — 2025-01-20

### Added
- Multi-file RAG support: `--context` / `-x` CLI flag
- Web UI multi-file context upload
- `jobstore.py` -- SQLite-backed persistent job store
- Roman numeral chapter detection with auto-conversion to Arabic
- Appendix/glossary/bibliography filtering

## [0.3.0] — 2025-01-20

### Added
- Subject-type detection (STEM/math/language/humanities)
- XML-tagged prompt structure for stricter LLM compliance
- Answer key checkbox in web UI
- `GET /api/jobs` endpoint
- Test suite: 39 tests

## [0.2.0] — 2025-01-20

### Added
- `validator.py` -- output validation with auto-retry
- `studycraft validate` CLI command
- Progress callback + web UI chapter-level progress
- Answer key generation (`--with-answers`)

## [0.1.0] — 2025-01-20

### Added
- Universal document loader (PDF, DOCX, TXT, MD, RTF)
- Auto chapter + subchapter detection
- RAG index via ChromaDB + MiniLM
- DuckDuckGo web research per chapter
- LLM generation via OpenRouter
- Export: Markdown -> HTML -> PDF
- Typer CLI + FastAPI web UI
