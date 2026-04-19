# Changelog

All notable changes to StudyCraft will be documented in this file.

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
