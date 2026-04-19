# Changelog

All notable changes to StudyCraft will be documented in this file.

## [0.3.0] — 2025-01-20

### Added
- Subject-type detection in `template.py` — classifies subjects as STEM, math, language, or humanities
- Format-specific example hints injected into LLM prompt per subject type
- XML-tagged prompt structure in `engine.py` for stricter LLM compliance
- Answer key checkbox in web UI form
- `GET /api/jobs` endpoint for listing all jobs
- Test suite: 39 tests across 5 modules (loader, detector, validator, export, template)
- `tests/` directory with `test_loader.py`, `test_detector.py`, `test_validator.py`, `test_export.py`, `test_template.py`

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
