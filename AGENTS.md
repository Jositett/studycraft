# AGENTS.md

## Commands

```bash
uv sync                                  # Install dependencies
uv run studycraft                        # Launch web UI (default)
uv run studycraft generate "doc.pdf"     # Full guide generation
uv run studycraft inspect "doc.pdf"      # Preview chapter outline
uv run studycraft inspect "doc.pdf" --rag # Show RAG chunks per chapter
uv run studycraft validate "guide.md"    # Check guide quality
uv run studycraft export "guide.md"      # Re-export to all formats
uv run studycraft gist "guide.md"        # Publish as GitHub Gist
uv run studycraft models --free --vision # List free vision models

# Generate options
-c, --chapter 3          # Generate single chapter
-r, --resume-from 5      # Resume from chapter (uses cache)
-s, --subject "Math"     # Override subject name
-m, --model <id>         # Specify OpenRouter model (default: openrouter/free)
-x, --context "extra.pdf" # Add supplementary RAG context files
-w, --workers 3          # Parallel generation
-t, --theme "dracula"     # Export theme (dark, light, nord, solarized, dracula, github, monokai, ocean, rose-pine)
--with-answers           # Generate answer key
--clear-cache            # Delete cached chapters
--rate-limit 5           # Seconds between chapters (default: 5)

# Windows: set UTF-8 encoding first
$env:PYTHONIOENCODING="utf-8"; uv run studycraft generate "doc.pdf"
```

## Env Required

Set `OPENROUTER_API_KEY` (or `STUDYCRAFT_API_KEY`) in `.env`. Get free key at <https://openrouter.ai>.

## CI & Release

```bash
uv run python scripts/ci.py              # Full CI: lint + test + build
uv run python scripts/ci.py --lint       # Lint only
uv run python scripts/ci.py --test       # Test only
uv run python scripts/release.py 0.8.0   # CI + bump version + tag + build
```

## Architecture

- Entry point: `src/studycraft/cli.py` -- no args launches web UI
- Engine: `engine.py` -- orchestrates load -> detect -> RAG -> research -> generate -> export
- Document loading: `loader.py` -- PDF, DOCX, TXT, MD, RTF, EPUB
- Chapter detection: `detector.py` -- numbered, Roman numeral, ALL-CAPS, fixed-window fallback
- RAG: `rag.py` -- ChromaDB + sentence-transformers with chunk metadata
- Web research: `researcher.py` -- DuckDuckGo per chapter
- Validation: `validator.py` -- checks sections, examples, quiz, placeholders
- Themes: `themes.py` -- 9 themes (dark, light, nord, solarized, dracula, github, monokai, ocean, rose-pine)
- Export: `export.py` + `export_docx.py` + `export_epub.py` -- MD, HTML, PDF, DOCX, EPUB (all themed + TOC)
- Models: `model_registry.py` -- fetches from OpenRouter API, caches to ~/.studycraft/models.json
- Job store: `jobstore.py` -- SQLite-backed persistent job tracking
- Web UI: `web.py` -- FastAPI + inline HTML

## Output

Generated to `./output/` by default:

- `<Subject>_Practice_Guide.md`
- `<Subject>_Practice_Guide.html`
- `<Subject>_Practice_Guide.pdf`
- `<Subject>_Practice_Guide.docx`
- `<Subject>_Practice_Guide.epub`
- `<Subject>_Answer_Key.md` (with --with-answers)
- `.cache/ch01.md` ... chN.md (crash recovery)

## Docker

```bash
docker compose up -d                     # Self-host web UI
docker run -p 8000:8000 --env-file .env studycraft  # Quick run
```
