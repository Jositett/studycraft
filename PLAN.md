# 🗺️ StudyCraft — Development Plan

## Status: v0.9.0 — Difficulty Levels, Review Step, Model Switching ✅

### What's working
- ✅ Universal document loader (PDF, DOCX, TXT, MD, RTF, EPUB)
- ✅ Auto chapter + subchapter detection (3 strategies with fallback)
- ✅ RAG index (ChromaDB + MiniLM) — clears between documents
- ✅ Subject-aware web research (ddgs, multi-query per chapter)
- ✅ Universal practice guide template (8 sections, subject-agnostic)
- ✅ LLM generation via OpenRouter with auto model switching (up to 5 fallbacks)
- ✅ Difficulty levels: beginner, intermediate, advanced
- ✅ Post-generation review step (auto-fixes unfilled placeholders)
- ✅ Model health testing (1-token probe, 6h cache)
- ✅ Per-chapter cache + `--resume-from` crash recovery
- ✅ Export pipeline: MD → HTML → PDF → DOCX → EPUB (all with TOC + themes)
- ✅ 9 built-in themes
- ✅ Pause/stop controls in web UI
- ✅ Typer CLI with Rich output, progress bars, `--theme`, `--difficulty`
- ✅ Web UI (dark mode, dynamic models, drag & drop context files)
- ✅ `uv`-managed project with editable install

---

## Phase 2 — Web UI (Complete the scaffold)

### 2.1 Real-time progress
- [ ] Wire engine events into `_jobs[job_id]` updates (currently only 2 progress points)
- [ ] Add chapter-level progress: "Generating chapter 3 of 12…"
- [ ] Stream LLM tokens to the browser via SSE (Server-Sent Events)
- [ ] Show detected outline in the UI before generation starts

### 2.2 Multi-file support
- [ ] Allow uploading multiple supplementary PDFs (merged into RAG, not all generated)
- [ ] "Add context files" button — index extras without treating them as a second document

### 2.3 Output management
- [ ] Job history page — list all past generated guides
- [x] Store jobs in SQLite (replace in-memory `_jobs` dict)
- [ ] Auto-cleanup of old job files after 24 hours

### 2.4 API
- [ ] `POST /api/generate` already exists — document and stabilise
- [ ] Add `GET /api/jobs` for history
- [ ] Auth header support so the web UI can be deployed safely

---

## Phase 3 — Generation Quality

### 3.1 Output validation
- [x] `validator.py` — check each generated chapter for:
  - All 8 section headings present
  - At least 3 worked examples
  - All 10 quiz questions populated
  - No unfilled `[...]` placeholders remaining
- [x] Auto-retry once on validation failure (different temperature)
- [ ] `uv run studycraft validate output/guide.md` command

### 3.2 Smarter prompting
- [ ] Inject one complete example chapter as a few-shot prefix
- [ ] XML-tagged sections for stricter LLM compliance
- [ ] Per-subject prompt tuning: detect if subject is STEM, humanities, language, etc.
  and adjust example format (code vs equations vs prose vs vocabulary)

### 3.3 Answer key generation
- [x] After generating all chapters, make a second pass to produce an `Answer_Key.md`
  with quiz answers, exercise solutions, and mini-project guidance
- [x] `--with-answers` flag on `generate`

---

## Phase 4 — Document Intelligence

### 4.1 Better chapter detection
- [ ] Use an LLM call to extract the table of contents if naive regex fails
- [ ] Support non-Western chapter markers (e.g. Arabic numerals, Roman numerals)
- [ ] Detect and handle appendices, glossaries, bibliographies — skip or summarise them

### 4.2 Richer RAG
- [ ] Upgrade embeddings: benchmark `all-mpnet-base-v2` vs `all-MiniLM-L6-v2`
- [ ] Store chunk metadata: chapter number, page number, source file
- [ ] `studycraft inspect --rag` — show which RAG chunks would be used per chapter

### 4.3 Image extraction
- [ ] Extract images from PDF/DOCX and describe them via vision model
- [ ] Include diagram descriptions in the chapter context

---

## Phase 5 — Output Formats & Integrations

### 5.1 Additional export formats
- [ ] DOCX export (using `python-docx`) — for learners who want to annotate in Word
- [ ] EPUB export — for e-reader compatibility
- [ ] Anki flashcard deck (`.apkg`) — auto-generate cards from quiz questions and definitions

### 5.2 Integrations
- [ ] Notion API — push guide chapters as Notion pages
- [x] GitHub Gist — one-click publish the Markdown guide
- [ ] Google Docs — export via Drive API

---

## Phase 6 — Automation & CI

### 6.1 Parallel generation
- [ ] `asyncio.gather` for concurrent chapter generation
- [ ] Token budget manager — pause if rate limit approaches
- [x] `--workers N` flag

### 6.2 GitHub Actions
- [ ] Workflow: regenerate guide when source document changes (git push trigger)
- [ ] Upload `.md`, `.html`, `.pdf` to GitHub Release
- [ ] Cache `rag_index/` and `.venv/` for fast reruns

### 6.3 Pytest suite
- [ ] `tests/test_loader.py` — load a sample PDF, DOCX, TXT
- [ ] `tests/test_detector.py` — parametrised detection tests across heading styles
- [ ] `tests/test_export.py` — generate minimal markdown, verify HTML is valid

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| `uv` package manager | Fastest resolver, built-in lockfile, great DX |
| ChromaDB (local) | Zero-config vector store, no server needed |
| `all-MiniLM-L6-v2` | Fast, small, strong retrieval quality |
| OpenRouter (not direct API) | Free model access; single API for all providers |
| Per-chapter cache files | Enables crash recovery without regenerating everything |
| FastAPI for web UI | Async, clean API, great docs at `/docs` automatically |
| In-memory job store (v0.1) | Simple; replace with SQLite in Phase 2.3 |
| Subject auto-detection | First meaningful line of document or filename stem |
| 3-strategy chapter detector | Handles structured textbooks, lecture notes, and unstructured text |

---

## Known Limitations (v0.1.0)

| Issue | Workaround |
|-------|-----------|
| Free LLM models may leave `[...]` placeholders unfilled | Use `--model meta-llama/llama-3.3-70b-instruct:free` or a paid model |
| Scanned PDF pages (image-only) yield no text | Use a PDF with a text layer; OCR support coming in Phase 4 |
| `embeddings.position_ids UNEXPECTED` log | Harmless — known upstream issue in sentence-transformers, model works fine |

---

## File Map

```
studycraft/
├── src/studycraft/
│   ├── __init__.py       — Package entry, exposes StudyCraft
│   ├── cli.py            — Typer CLI: generate, inspect, export, validate, models, gist
│   ├── engine.py         — Core orchestrator (StudyCraft class)
│   ├── loader.py         — Document loader: PDF, DOCX, TXT, MD, RTF, EPUB
│   ├── detector.py       — Chapter + subchapter auto-detection
│   ├── rag.py            — ChromaDB RAG index
│   ├── researcher.py     — DuckDuckGo web research
│   ├── template.py       — Universal 8-section practice guide template
│   ├── themes.py         — Theme registry (9 themes, Theme dataclass)
│   ├── validator.py      — Output validation (sections, examples, quiz, placeholders)
│   ├── export.py         — MD → HTML → PDF export with TOC + themes
│   ├── export_docx.py    — DOCX export with TOC + themes
│   ├── export_epub.py    — EPUB export with TOC + themes
│   ├── model_registry.py — OpenRouter model fetcher + cache
│   ├── jobstore.py       — SQLite-backed persistent job tracking
│   └── web.py            — FastAPI web UI + background job runner
├── pyproject.toml        — uv/hatch config, deps, entry points
├── .env.example          — API key template
├── README.md             — User-facing docs
└── PLAN.md               — This file
```
