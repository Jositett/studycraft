# Task Tracker

## Current Sprint — v0.5.0

### Phase 4.2 — Richer RAG
- [ ] Benchmark `all-mpnet-base-v2` vs `all-MiniLM-L6-v2`
- [ ] Store chunk metadata: chapter number, page number, source file
- [ ] `studycraft inspect --rag` — show RAG chunks per chapter

### Phase 5.1 — Additional Export Formats
- [ ] DOCX export (python-docx)
- [ ] EPUB export
- [ ] Anki flashcard deck (.apkg)

### Phase 6.1 — Parallel Generation
- [ ] `asyncio.gather` for concurrent chapter generation
- [ ] Token budget manager
- [ ] `--workers N` flag

---

## Backlog

### Phase 5.2 — Integrations
- [ ] Notion API — push guide chapters as Notion pages
- [ ] GitHub Gist — one-click publish
- [ ] Google Docs — export via Drive API

### Phase 6.2 — GitHub Actions
- [ ] Workflow: regenerate guide on source doc change
- [ ] Upload artifacts to GitHub Release
- [ ] Cache rag_index/ and .venv/

---

## Completed

### v0.4.0 — Multi-file RAG, SQLite Jobs & Better Detection ✅
- [x] `--context` / `-x` CLI flag for supplementary RAG files
- [x] Web UI multi-file context upload
- [x] SQLite job store (`jobstore.py`) replacing in-memory dict
- [x] Auto-cleanup of jobs older than 24h
- [x] Roman numeral chapter detection (I, II, III, IV…)
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
- [x] Web UI real-time chapter progress (10–95% granularity)
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
