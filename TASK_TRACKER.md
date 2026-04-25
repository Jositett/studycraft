# Task Tracker

## Backlog

### Phase 2.3 — Output Management
- [ ] Job history page — list all past generated guides in the web UI

### Phase 3.2 — Smarter Prompting
- [ ] Inject one complete example chapter as a few-shot prefix

### Phase 4.2 — Richer RAG
- [ ] Benchmark `all-mpnet-base-v2` vs `all-MiniLM-L6-v2` embeddings

### Phase 4.3 — Image Extraction
- [ ] Extract images from PDF/DOCX and describe via vision model
- [ ] Include diagram descriptions in chapter context

### Phase 5.1 — Additional Export Formats
- [ ] Anki flashcard deck (`.apkg`)

### Phase 5.2 — Integrations
- [ ] Notion API — push guide chapters as Notion pages
- [ ] Google Docs — export via Drive API

### Phase 6.1 — Parallel Generation
- [ ] Token budget manager — pause if rate limit approaches

### Phase 6.2 — GitHub Actions
- [ ] Workflow: regenerate guide when source document changes (git push trigger)
- [ ] Cache `rag_index/` and `.venv/` for fast reruns

---

## Completed

### v0.9.2 — Audio/Video Guides, Full Docker Extras ✅

- [x] Frontend checkboxes for Audio guide (`--with-audio`) and Video guide (`--with-video`)
- [x] `tts_engines.py` — Chatterbox, KittenTTS, Coqui/XTTS-v2, OpenRouter TTS adapters
- [x] `audio_generator.py` — orchestrates TTS with dependency injection
- [x] `video_generator.py` — OpenRouter video API (async, free models only)
- [x] `video_composer.py` — combines video + audio + text overlays (videopython/ffmpeg fallback)
- [x] `generate-audio` and `generate-video` CLI commands
- [x] Dockerfile installs full extras (pdf + tts + video)
- [x] `scripts/deploy.py` cross-platform compatibility (shutil.copy)
- [x] Usage Guide section in web UI updated with audio/video/multimedia features
- [x] HuggingFace deploy script uses modern `hf` CLI

### v0.9.1 — Critical Fixes, SSE Streaming, Auth ✅

- [x] SSE streaming endpoint `/api/stream/{job_id}` (replaces polling)
- [x] API key authentication via `STUDYCRAFT_WEB_TOKEN`
- [x] LLM-assisted TOC extraction fallback in `detector.py`
- [x] Per-query research cache in `~/.studycraft/research_cache.json` (6h TTL)
- [x] Configurable 8s timeout per DuckDuckGo query
- [x] `JobStore` module-level singleton with startup/shutdown lifecycle (race condition fix)
- [x] Parallel worker loop respects `on_check_control` for pause/stop
- [x] RAG chunk IDs sanitized to valid characters
- [x] EPUB loader block vs inline tag separation (preserves paragraph structure)
- [x] Answer key generator caps sections before joining (avoids token overflow)
- [x] `JobStore.update()` validates column names (SQL injection prevention)
- [x] `engine.py` extracted `_build_prompt()` method for testability
- [x] Web UI moved to `templates/index.html` (Jinja2, autoescape)
- [x] `model_registry.fetch_models()` retries 3× with 2s delay
- [x] Full `ruff` config (line-length 100, target py312), codebase auto-formatted
- [x] `tests/test_engine.py` — mocked LLM end-to-end test
- [x] `tests/test_web.py` — FastAPI test client tests
- [x] `pytest-asyncio` added to dev deps, `asyncio_mode = "auto"`
- [x] 96 tests passing

### v0.9.0 — Difficulty Levels, Review Step, Model Switching ✅

- [x] Difficulty levels (beginner/intermediate/advanced) — CLI + web UI + prompt injection
- [x] Post-generation review step — auto-fixes unfilled placeholders
- [x] Auto model switching on persistent failure (up to 5 fallbacks)
- [x] Model health testing (1-token probe, 6h cache at `~/.studycraft/model_health.json`)
- [x] `POST /api/models/test` endpoint
- [x] `/api/models` prioritizes healthy models in dropdown
- [x] Pause/stop controls in web UI progress card
- [x] `POST /api/control/{job_id}` endpoint for pause/stop/resume
- [x] Context files drag & drop zone with file list and remove buttons
- [x] Replaced `duckduckgo-search` with `ddgs`
- [x] PDF emoji fix, progress tracking fix
- [x] Release script bumps version in all 3 files
- [x] 53 tests passing

### v0.8.0 — Theme System + TOC Navigation ✅

- [x] `themes.py` with Theme dataclass and 9 themes (dark, light, nord, solarized, dracula, github, monokai, ocean, rosé-pine)
- [x] All exports (HTML, PDF, DOCX, EPUB) use theme-driven colors via dependency injection
- [x] TOC with navigation in all formats (HTML sidebar, PDF TOC page, MD anchors, DOCX Word TOC field)
- [x] `--theme` / `-t` CLI flag + web UI theme dropdown
- [x] Dark mode default with proper contrast for HTML exports
- [x] 53 tests passing

### v0.7.0 — EPUB Upload, Dark Mode UI, Bug Fixes ✅

- [x] EPUB file upload support (loader + web UI + CLI)
- [x] Dark mode web UI with improved UX (scrollbar, aside guide, time estimates)
- [x] Dynamic model selection from OpenRouter API with refresh button
- [x] Favicon, "Generate another" button, file-selected drop zone state
- [x] Replaced weasyprint (GTK) with fpdf2 (pure Python) for PDF export
- [x] 429 rate-limit retry with exponential backoff
- [x] HF_TOKEN support in .env
- [x] 53 tests passing

### v0.6.0 — EPUB Export, GitHub Actions, Gist Publish ✅

- [x] EPUB export via `export_epub.py` (ebooklib) in pipeline
- [x] GitHub Actions CI workflow (lint + test on push/PR)
- [x] GitHub Actions release workflow (build + upload on tag)
- [x] `studycraft gist` CLI command — publish guide as GitHub Gist
- [x] 48 tests passing

### v0.5.0 — Richer RAG, DOCX Export, Parallel Generation ✅

- [x] RAG chunk metadata (source, chunk_index)
- [x] `query_detailed()` and `chunk_count()` methods on RAGIndex
- [x] `studycraft inspect --rag` — show RAG chunks per chapter
- [x] DOCX export via `export_docx.py` in pipeline
- [x] Parallel generation with `--workers N` / `-w N` (ThreadPoolExecutor)
- [x] 47 tests passing

### v0.4.0 — Multi-file RAG, SQLite Jobs, Better Detection ✅

- [x] `--context` / `-x` CLI flag for supplementary RAG files
- [x] Web UI multi-file context upload
- [x] SQLite job store (`jobstore.py`) replacing in-memory dict
- [x] Auto-cleanup of jobs older than 24h
- [x] Roman numeral chapter detection
- [x] Appendix/glossary/bibliography/references filtering
- [x] 46 tests passing

### v0.3.0 — Smarter Prompting, Tests, API ✅

- [x] XML-tagged prompt sections for stricter LLM compliance
- [x] Subject-type detection (STEM/math/language/humanities)
- [x] Format-specific example hints per subject type
- [x] Answer key checkbox wired into web UI
- [x] `GET /api/jobs` endpoint
- [x] 39 tests passing

### v0.2.0 — Validation, Progress, Answer Keys ✅

- [x] Output validator with 4 checks (sections, examples, quiz, placeholders)
- [x] Auto-retry on validation failure (higher temperature)
- [x] `studycraft validate` CLI command
- [x] Engine progress callback for chapter-level updates
- [x] Web UI real-time chapter progress
- [x] Answer key generation via `--with-answers` flag

### v0.1.0 — Core Pipeline ✅

- [x] Document loader (PDF, DOCX, TXT, MD, RTF)
- [x] Chapter + subchapter detection (3 strategies)
- [x] RAG index (ChromaDB + MiniLM)
- [x] Web research (DuckDuckGo)
- [x] LLM generation via OpenRouter
- [x] Per-chapter cache + crash recovery
- [x] Export: MD → HTML → PDF
- [x] CLI (generate, inspect, export, models)
- [x] Web UI scaffold
