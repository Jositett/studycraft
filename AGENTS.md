# AGENTS.md

## Commands

```bash
uv sync                  # Install dependencies
uv run studycraft generate "doc.pdf"    # Full guide generation
uv run studycraft inspect "doc.pdf"     # Preview chapter outline only
uv run studycraft export "guide.md"      # Re-export to HTML/PDF
uv run studycraft models                 # List recommended models

# Options
-c, --chapter 3          # Generate single chapter
-r, --resume-from 5      # Resume from chapter (uses cache)
-s, --subject "Math"     # Override subject name
-m, --model <id>         # Specify OpenRouter model (default: openrouter/free)
--clear-cache            # Delete cached chapters
--rate-limit             # Seconds between chapters (default: 5, for free tier)

# Windows: set UTF-8 encoding first
$env:PYTHONIOENCODING="utf-8"; uv run studycraft generate "doc.pdf"
```

## Env Required

Set `OPENROUTER_API_KEY` (or `STUDYCRAFT_API_KEY`) in `.env`. Get free key at https://openrouter.ai.

## Linting & Testing

```bash
uv run ruff check src/        # Lint
uv run pytest                 # Tests (no tests yet)
```

## Architecture

- Entry point: `src/studycraft/cli.py` → `StudyCraft` class in `engine.py`
- Document loading: `loader.py` supports PDF, DOCX, TXT, MD, RTF
- Chapter detection: `detector.py` (numbered headings, ALL-CAPS, fixed-window fallback)
- RAG: `rag.py` uses chromadb with sentence-transformers
- Web research: `researcher.py` uses duckduckgo-search
- Export: `export.py` produces MD, HTML (via markdown), PDF (via weasyprint)

## Output

Generated to `./output/` by default:
- `<Subject>_Practice_Guide.md`
- `<Subject>_Practice_Guide.html`
- `<Subject>_Practice_Guide.pdf`
- `.cache/ch01.md` … chN.md (crash recovery)

## Web UI

```bash
uv add fastapi uvicorn python-multipart
uv run studycraft-web
# Open http://localhost:8000
```