# Task Tracker

## Backlog

### Phase 5.1 — Additional Export Formats (remaining)

- [ ] Anki flashcard deck (.apkg)

### Phase 5.2 — Integrations (remaining)

- [ ] Notion API -- push guide chapters as Notion pages
- [ ] Google Docs -- export via Drive API

### Phase 4.3 — Image Extraction

- [ ] Extract images from PDF/DOCX and describe via vision model
- [ ] Include diagram descriptions in chapter context

---

## Completed

### v0.6.0 — EPUB, GitHub Actions, Gist Publish ✅

- [x] EPUB export via `export_epub.py` (ebooklib) in pipeline
- [x] GitHub Actions CI workflow (lint + test on push/PR)
- [x] GitHub Actions release workflow (build + upload on tag)
- [x] `studycraft gist` CLI command -- publish guide as GitHub Gist
- [x] Version bumped to 0.6.0 in pyproject.toml
- [x] ebooklib added to dependencies
- [x] 48 tests passing (1 new)

### v0.5.0 — Richer RAG, DOCX Export & Parallel Generation ✅

- [x] RAG chunk metadata (source, chunk_index)
- [x] `query_detailed()` and `chunk_count()` methods on RAGIndex
- [x] `studycraft inspect --rag` -- show RAG chunks per chapter
- [x] DOCX export via `export_docx.py` in pipeline
- [x] Parallel generation with `--workers N` / `-w N` (ThreadPoolExecutor)
- [x] 47 tests passing (1 new)

### v0.4.0 — Multi-file RAG, SQLite Jobs & Better Detection ✅

- [x] `--context` / `-x` CLI flag for supplementary RAG files
- [x] Web UI multi-file context upload
- [x] SQLite job store (`jobstore.py`) replacing in-memory dict
- [x] Auto-cleanup of jobs older than 24h
- [x] Roman numeral chapter detection (I, II, III, IV...)
- [x] Appendix/glossary/bibliography/references filtering
- [x] 46 tests passing (7 new)

### v0.3.0 — Smarter Prompting, Tests & API ✅

- [x] XML-tagged prompt sections for stricter LLM compliance
- [x] Subject-type detection (STEM/math/language/humanities)
- [x] Format-specific example hints per subject type
- [x] Answer key checkbox wired into web UI
- [x] `GET /api/jobs` endpoint for job listing
- [x] Test suite: 39 tests across loader, detector, validator, export, template

### v0.2.0 — Validation, Progress & Answer Keys ✅

- [x] Output validator with 4 checks (sections, examples, quiz, placeholders)
- [x] Auto-retry on validation failure (higher temperature)
- [x] `studycraft validate` CLI command
- [x] Engine progress callback for chapter-level updates
- [x] Web UI real-time chapter progress (10-95% granularity)
- [x] Answer key generation via `--with-answers` flag

### v0.1.0 — Core Pipeline ✅

- [x] Document loader (PDF, DOCX, TXT, MD, RTF)
- [x] Chapter + subchapter detection (3 strategies)
- [x] RAG index (ChromaDB + MiniLM)
- [x] Web research (DuckDuckGo)
- [x] LLM generation via OpenRouter
- [x] Per-chapter cache + crash recovery
- [x] Export: MD -> HTML -> PDF
- [x] CLI (generate, inspect, export, models)
- [x] Web UI scaffold
