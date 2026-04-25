# 🗺️ StudyCraft — Development Plan

## Status: v0.9.2 — Audio/Video Guides, Full Docker Extras ✅

### What's working
- ✅ Universal document loader (PDF, DOCX, TXT, MD, RTF, EPUB)
- ✅ Auto chapter + subchapter detection (regex, Roman numerals, ALL-CAPS, LLM-assisted TOC fallback)
- ✅ RAG index (ChromaDB + MiniLM) — clears between documents, chunk metadata (source, page, index)
- ✅ Subject-aware web research (ddgs, multi-query per chapter, 6h cache, per-query timeout)
- ✅ Universal practice guide template (8 sections, subject-agnostic)
- ✅ LLM generation via OpenRouter with auto model switching (up to 5 fallbacks)
- ✅ Difficulty levels: beginner, intermediate, advanced
- ✅ Post-generation review step (auto-fixes unfilled placeholders)
- ✅ Model health testing (1-token probe, 6h cache)
- ✅ Per-chapter cache + `--resume-from` crash recovery
- ✅ Export pipeline: MD → HTML → PDF → DOCX → EPUB (all with TOC + themes)
- ✅ 9 built-in themes (dark, light, nord, solarized, dracula, github, monokai, ocean, rosé-pine)
- ✅ Pause/stop controls in web UI
- ✅ SSE streaming progress (real-time, replaces polling)
- ✅ Typer CLI with Rich output, progress bars, `--theme`, `--difficulty`
- ✅ Web UI (dark mode, dynamic models, drag & drop context files, BYOK)
- ✅ Optional bearer token auth (`STUDYCRAFT_WEB_TOKEN`)
- ✅ Audio guides — KittenTTS, Chatterbox, Coqui/XTTS-v2, OpenRouter TTS (free only)
- ✅ Video guides — OpenRouter video API (free models only), video composer
- ✅ `uv`-managed project with editable install, CPU-only torch override
- ✅ Docker + docker-compose with full extras (pdf + tts + video)
- ✅ SQLite job store (`jobstore.py`) with SQL injection prevention
- ✅ GitHub Actions CI/release workflows
- ✅ 96 tests passing

---

## Phase 2 — Web UI

### 2.1 Real-time progress
- [x] Wire engine events into `_jobs[job_id]` updates (chapter-level progress)
- [x] Stream LLM tokens to the browser via SSE (Server-Sent Events)
- [x] Show detected outline in the UI before generation starts
- [x] Parallel worker control — `on_check_control` respected in `ThreadPoolExecutor` path

### 2.2 Multi-file support
- [ ] Allow uploading multiple supplementary PDFs (merged into RAG, not all generated)
- [x] "Add context files" drag & drop zone — index extras without treating them as a second document

### 2.3 Output management
- [ ] Job history page — list all past generated guides in the UI
- [x] Store jobs in SQLite (`jobstore.py`)
- [x] Auto-cleanup of old job files after 24 hours
- [x] `GET /api/jobs` endpoint

### 2.4 API
- [x] `POST /api/generate` — documented and stable
- [x] `GET /api/jobs` for history
- [x] Auth header support (`STUDYCRAFT_WEB_TOKEN`)

---

## Phase 3 — Generation Quality

### 3.1 Output validation
- [x] `validator.py` — checks sections, examples, quiz, placeholders
- [x] Auto-retry once on validation failure (different temperature)
- [x] `studycraft validate output/guide.md` command

### 3.2 Smarter prompting
- [x] XML-tagged sections for stricter LLM compliance
- [x] Per-subject prompt tuning (STEM, humanities, language, math)
- [ ] Inject one complete example chapter as a few-shot prefix

### 3.3 Answer key generation
- [x] `Answer_Key.md` with quiz answers, exercise solutions, mini-project guidance
- [x] `--with-answers` flag on `generate`

---

## Phase 4 — Document Intelligence

### 4.1 Better chapter detection
- [x] LLM-assisted TOC extraction fallback when regex yields ≤1 chapter
- [x] Roman numeral chapter markers
- [x] Appendix/glossary/bibliography filtering

### 4.2 Richer RAG
- [x] Chunk metadata: chapter, page number, source file
- [x] `query_detailed()` and `chunk_count()` methods
- [x] `studycraft inspect --rag` — show RAG chunks per chapter
- [ ] Benchmark `all-mpnet-base-v2` vs `all-MiniLM-L6-v2`

### 4.3 Image extraction
- [ ] Extract images from PDF/DOCX and describe via vision model
- [ ] Include diagram descriptions in chapter context

---

## Phase 5 — Output Formats & Integrations

### 5.1 Additional export formats
- [x] DOCX export (`export_docx.py`)
- [x] EPUB export (`export_epub.py`)
- [ ] Anki flashcard deck (`.apkg`)

### 5.2 Integrations
- [x] GitHub Gist — `studycraft gist` command
- [ ] Notion API — push guide chapters as Notion pages
- [ ] Google Docs — export via Drive API

---

## Phase 6 — Automation & CI

### 6.1 Parallel generation
- [x] `--workers N` flag (ThreadPoolExecutor)
- [x] `on_check_control` respected in parallel path
- [ ] Token budget manager — pause if rate limit approaches

### 6.2 GitHub Actions
- [x] CI workflow: lint + test on push/PR
- [x] Release workflow: build + upload on tag
- [ ] Workflow: regenerate guide when source document changes
- [ ] Cache `rag_index/` and `.venv/` for fast reruns

### 6.3 Test suite
- [x] `tests/test_loader.py`
- [x] `tests/test_detector.py`
- [x] `tests/test_export.py`
- [x] `tests/test_engine.py` (mocked LLM)
- [x] `tests/test_web.py` (FastAPI test client)
- [x] 96 tests passing

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------| 
| `uv` package manager | Fastest resolver, built-in lockfile, CPU-only torch override |
| ChromaDB (local) | Zero-config vector store, no server needed |
| `all-MiniLM-L6-v2` | Fast, small, strong retrieval quality |
| OpenRouter (not direct API) | Free model access; single API for all providers |
| Per-chapter cache files | Enables crash recovery without regenerating everything |
| FastAPI + Jinja2 | Async, clean API, templates in `src/studycraft/templates/` |
| SQLite job store | Persistent, zero-config, safe concurrent access |
| SSE for progress | Real-time updates without polling overhead |
| TTS dependency injection | Swap engines without changing generation logic |
| Free-only video/TTS cloud | Prevents unexpected billing on OpenRouter |

---

## Known Limitations

| Issue | Workaround |
|-------|-----------|
| Free LLM models may leave `[...]` placeholders | Use `--model meta-llama/llama-3.3-70b-instruct:free` or a paid model |
| Scanned PDF pages (image-only) yield no text | Use a PDF with a text layer; OCR support planned in Phase 4.3 |
| `embeddings.position_ids UNEXPECTED` log | Harmless — known upstream issue in sentence-transformers |
| Coqui/XTTS-v2 requires ~1.7GB download on first use | Pre-download with `uv run python -c "from TTS.api import TTS; TTS('tts_models/multilingual/multi-dataset/xtts_v2')"` |

---

## File Map

```
studycraft/
├── src/studycraft/
│   ├── __init__.py          — Package entry, exposes StudyCraft
│   ├── cli.py               — Typer CLI: generate, inspect, export, validate, models, gist, generate-audio, generate-video
│   ├── engine.py            — Core orchestrator (StudyCraft class)
│   ├── loader.py            — Document loader: PDF, DOCX, TXT, MD, RTF, EPUB
│   ├── detector.py          — Chapter + subchapter auto-detection (regex + LLM fallback)
│   ├── rag.py               — ChromaDB RAG index with chunk metadata
│   ├── researcher.py        — DuckDuckGo web research + 6h cache
│   ├── template.py          — Universal 8-section practice guide template
│   ├── themes.py            — Theme registry (9 themes, Theme dataclass)
│   ├── validator.py         — Output validation (sections, examples, quiz, placeholders)
│   ├── export.py            — MD → HTML → PDF export with TOC + themes
│   ├── export_docx.py       — DOCX export with TOC + themes
│   ├── export_epub.py       — EPUB export with TOC + themes
│   ├── tts_engines.py       — TTS engine adapters (Chatterbox, KittenTTS, Coqui, OpenRouter)
│   ├── audio_generator.py   — Audio guide orchestrator
│   ├── video_generator.py   — OpenRouter video generation (async, free models only)
│   ├── video_composer.py    — Video + audio + text overlay composition
│   ├── model_registry.py    — OpenRouter model fetcher + health cache
│   ├── jobstore.py          — SQLite-backed persistent job tracking
│   ├── web.py               — FastAPI web UI + SSE streaming
│   └── templates/
│       └── index.html       — Web UI (Jinja2)
├── scripts/
│   ├── ci.py                — Full CI: lint + test + build
│   ├── release.py           — Version bump + tag + build
│   └── deploy.py            — HuggingFace Spaces & local Docker Compose deployment
├── tests/                   — pytest suite (96 tests)
├── pyproject.toml           — uv/hatch config, deps, entry points
├── Dockerfile               — Full extras (pdf + tts + video)
├── docker-compose.yml
├── .env.example             — API key template
└── README.md
```
