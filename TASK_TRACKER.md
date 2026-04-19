# Task Tracker

## Current Sprint — v0.2.0

### Phase 3.1 — Output Validation
- [x] `validator.py` — check generated chapters for required sections, examples, quiz questions, unfilled placeholders
- [x] Auto-retry on validation failure (different temperature)
- [x] `studycraft validate <guide.md>` CLI command

### Phase 2.1 — Web UI Real-time Progress
- [x] Add progress callback to engine so callers get chapter-level updates
- [x] Wire callback into web `_jobs` dict for per-chapter progress
- [x] Show "Generating chapter N of M…" in browser

### Phase 3.3 — Answer Key Generation
- [x] Second LLM pass to produce `Answer_Key.md` with quiz answers + exercise solutions
- [x] `--with-answers` flag on `generate` command
- [ ] Include answer key in web UI output

---

## Backlog

### Phase 2.2 — Multi-file Support
- [ ] Allow uploading supplementary PDFs merged into RAG
- [ ] "Add context files" button in web UI

### Phase 2.3 — Persistent Job Store
- [ ] Replace in-memory `_jobs` dict with SQLite
- [ ] Job history page
- [ ] Auto-cleanup of old jobs after 24h

### Phase 3.2 — Smarter Prompting
- [ ] Few-shot example chapter prefix
- [ ] XML-tagged sections for stricter compliance
- [ ] Per-subject prompt tuning (STEM vs humanities vs language)

### Phase 4.1 — Better Chapter Detection
- [ ] LLM-based TOC extraction fallback
- [ ] Non-Western chapter markers
- [ ] Appendix/glossary detection

### Phase 6.3 — Test Suite
- [ ] `tests/test_loader.py`
- [ ] `tests/test_detector.py`
- [ ] `tests/test_export.py`

---

## Completed

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
