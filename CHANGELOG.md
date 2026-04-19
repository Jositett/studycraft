# Changelog

All notable changes to StudyCraft will be documented in this file.

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
