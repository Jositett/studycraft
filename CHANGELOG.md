# Changelog

All notable changes to StudyCraft will be documented in this file.

## [0.4.0] — 2025-01-20

### Added
- Multi-file RAG support: `--context` / `-x` CLI flag to index supplementary files into RAG without generating chapters from them
- Web UI "Additional context files" multi-file upload field
- `jobstore.py` — SQLite-backed persistent job store (replaces in-memory dict)
- Auto-cleanup of jobs older than 24 hours on server startup
- Roman numeral chapter detection ("Chapter I", "Chapter IV", etc.) with auto-conversion to Arabic
- Appendix, glossary, bibliography, references, and index sections are now filtered out of chapter detection
- `GET /api/jobs` now returns persistent job history
- 7 new tests: Roman numerals, appendix filtering, SQLite job store CRUD

### Changed
- `engine.py` — `run()` accepts `context_files` parameter for supplementary RAG documents
- `detector.py` — added Roman numeral pattern, `_roman_to_int()` helper, `_SKIP_PATTERN` filter
- `web.py` — replaced `_jobs` dict with `JobStore`; generate endpoint accepts `context_files`

## [0.3.0] — 2025-01-20

### Added
- Subject-type detection in `template.py` — classifies subjects as STEM, math, language, or humanities
- Format-specific example hints injected into LLM prompt per subject type
- XML-tagged prompt structure in `engine.py` for stricter LLM compliance
- Answer key checkbox in web UI form
- `GET /api/jobs` endpoint for listing all jobs
- Test suite: 39 tests across 5 modules (loader, detector, validator, export, template)

### Changed
- `engine.py` — prompt now uses XML tags (`<subject>`, `<document_context>`, `<rules>`, etc.)
- `template.py` — now exports `detect_subject_type()` and `example_format_hint()`
- `web.py` — generate endpoint accepts `with_answers` form field; added `/api/jobs`

## [0.2.0] — 2025-01-20

### Added
- `validator.py` — checks generated chapters for required sections, worked examples, quiz questions, and unfilled placeholders
- Auto-retry on validation failure with higher temperature
- `studycraft validate <guide.md>` CLI command
- Progress callback in engine for chapter-level updates
- Web UI now shows "Generating chapter N of M…" with granular progress bar
- Answer key generation (`--with-answers` flag) — second LLM pass produces `Answer_Key.md`

### Changed
- `engine.py` — `_generate_chapter` now accepts `temperature` parameter; new `_generate_chapter_with_retry` wrapper
- `engine.py` — `run()` accepts `on_progress` callback and `with_answers` flag
- `web.py` — background job runner wires progress callback (10–95% range)

## [0.1.0] — 2025-01-20

### Added
- Universal document loader (PDF, DOCX, TXT, MD, RTF)
- Auto chapter + subchapter detection (numbered, ALL-CAPS, fixed-window fallback)
- RAG index via ChromaDB + MiniLM embeddings
- Subject-aware DuckDuckGo web research per chapter
- LLM generation via OpenRouter (any model, configurable)
- Universal 8-section practice guide template
- Per-chapter cache + `--resume-from` crash recovery
- Export pipeline: Markdown → styled HTML → PDF
- Typer CLI with Rich output and progress bars
- Web UI scaffold (FastAPI + drag-and-drop, background jobs, polling)
- `uv`-managed project with editable install + optional web deps
