# StudyCraft — Comprehensive Review & Improvement Prompt (COMPLETED ✅)

**Status:** All items implemented and committed  
**Version:** 0.9.1 (post-improvement release)  
**Date:** 2026-04-25

---

## Original Prompt

Use this prompt with Claude Code (or any capable agent) in the `C:\Self_Projects\studycraft` directory.

---

## PROMPT

You are a senior Python engineer doing a full review of the **StudyCraft** project (`src/studycraft/`). This is a v0.9.0 CLI + web tool that generates structured practice guides from documents using an LLM (OpenRouter), RAG (ChromaDB), and web research (DuckDuckGo). Read all files before making any changes.

Apply **all** of the following fixes and improvements in order. Commit after each logical group.

---

## GROUP 1 — Package Management (Critical Fix: `uv sync` Wipes Packages)

### 1.1 — The Root Cause
`uv sync` wipes packages that are not in `pyproject.toml` because that is its design: it makes the env exactly match the lockfile. The current `pyproject.toml` is missing `[tool.uv]` configuration for overrides. The primary issue is that `sentence-transformers` pulls in a full CUDA PyTorch stack (~2GB) when syncing on CPU machines, and this can cause the resolver to fail or conflict — leading to packages being removed and not reinstalled.

**Fix `pyproject.toml`** — add a `[tool.uv]` section with a CPU-only PyTorch override so `uv sync` never pulls CUDA:

```toml
[tool.uv]
# Force CPU-only PyTorch — avoids pulling ~2GB CUDA wheels that conflict on Windows/CPU machines.
# This is the same fix used in the Dockerfile (UV_TORCH_BACKEND=cpu).
# Without this, `uv sync` may silently remove packages mid-resolution when the CUDA index conflicts.
torch-backend = "cpu"

[tool.uv.pip]
# Always reinstall the editable package on sync so CLI entry points are never lost
reinstall-package = ["studycraft"]
```

Also add a `.env`-level note and a `README` section explaining:
- Never `pip install` anything into the venv directly; always use `uv add <package>` to keep `pyproject.toml` and `uv.lock` in sync.
- Run `uv sync --frozen` to reinstall without re-resolving (safe when the lockfile is trusted).
- Run `uv sync` (without `--frozen`) only when intentionally updating dependency versions.

### 1.2 — Dependency version hygiene
In `pyproject.toml`, the `fastapi` pin is `>=0.136.0`. This is fine (0.136.1 is the latest as of writing), but `openai>=2.32.0` is suspicious — the openai package uses a v1 SDK versioning scheme and `2.x` does not exist yet on PyPI. Verify and correct:

```toml
# Correct these lines:
"openai>=1.82.0",           # was: openai>=2.32.0 (non-existent version)
"chromadb>=0.6.0",          # was: chromadb>=1.5.8 (verify actual latest)
```

Check PyPI for the actual latest versions of `chromadb`, `openai`, `sentence-transformers`, `ddgs`, and `playwright` before pinning.

### 1.3 — Split dev and optional deps properly
`playwright` is a heavy dependency (~100MB) only needed for PDF export via Chromium. Move it to an optional group so users who don't need PDF can skip it:

```toml
[project.optional-dependencies]
pdf = ["playwright>=1.50.0"]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.25",
    "ruff>=0.4",
    "httpx>=0.27",   # for FastAPI test client
]
```

Update `AGENTS.md` with: `uv sync --extra pdf` for full install, `uv sync` for no-Playwright install.

---

## GROUP 2 — Critical Bug Fixes

### 2.1 — `web.py`: JobStore instantiated inside endpoint (race condition)
**File:** `src/studycraft/web.py`

Currently `JobStore` is instantiated inside the `@app.post("/api/generate")` handler:
```python
# CURRENT (bad — new DB connection per request, potential WAL conflicts)
store = JobStore(db_path=OUTPUT_DIR / "jobs.db")
```

Fix: instantiate `JobStore` once at module level (after the FastAPI app is created) and close it on shutdown:

```python
# After app = FastAPI(...):
_store: JobStore | None = None

@app.on_event("startup")
async def _startup():
    global _store
    _store = JobStore(db_path=OUTPUT_DIR / "jobs.db")

@app.on_event("shutdown")
async def _shutdown():
    if _store:
        _store._conn.close()
```

Replace all local `store = JobStore(...)` usages in endpoints with the global `_store`.

### 2.2 — `engine.py`: Parallel workers don't respect `on_check_control`
**File:** `src/studycraft/engine.py`, `_generate_all()`

In the `workers > 1` branch, `on_check_control` is never called — the pause/stop control from the web UI only works in sequential mode. Fix:

```python
# In the parallel branch, after each future.result():
if on_check_control:
    signal = on_check_control()
    if signal == "stop":
        pool.shutdown(wait=False, cancel_futures=True)
        console.print("[yellow]Generation stopped by user[/yellow]")
        break
    # For "pause": poll until signal clears (add a short sleep loop)
```

### 2.3 — `rag.py`: Chunk IDs collide across context files
**File:** `src/studycraft/rag.py`, `index()`

IDs are generated as `{source_name}_{i}`. If `source_name` contains spaces or special characters, ChromaDB may reject or silently truncate them. Fix:

```python
import re
safe_source = re.sub(r"[^\w-]", "_", source_name)
ids = [f"{safe_source}_{i}" for i in range(len(chunks))]
```

### 2.4 — `loader.py`: EPUB parsing strips structural whitespace
**File:** `src/studycraft/loader.py`, `_load_epub()`

`re.sub(r"<[^>]+>", " ", html)` replaces all tags with a space, which concatenates words that were in adjacent inline elements. Use a smarter approach:

```python
# Replace block-level tags with newlines, inline tags with space
html = re.sub(r"<(p|div|h\d|li|br|tr)[^>]*>", "\n", html, flags=re.IGNORECASE)
clean = re.sub(r"<[^>]+>", " ", html)
clean = re.sub(r"[ \t]+", " ", clean)
clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
```

### 2.5 — `engine.py`: `_generate_answer_key` slices a joined list incorrectly
**File:** `src/studycraft/engine.py`, `_generate_answer_key()`

```python
# CURRENT (wrong — joins a list then slices the resulting string by character count)
f\"{chr(10).join(sections[:6000])}\"

# FIX — slice the list before joining, and cap individual section length
capped = [s[:1500] for s in sections[:20]]
"\n\n".join(capped)
```

### 2.6 — `jobstore.py`: SQL injection via `**kwargs` in `update()`
**File:** `src/studycraft/jobstore.py`, `update()`

Column names are interpolated directly into the SQL string from the `kwargs` keys. While callers are internal, this is still a risk and will cause silent failures if a key has a typo. Validate allowed columns:

```python
_ALLOWED_COLS = {"status", "progress", "message", "files", "control"}

def update(self, job_id: str, **kwargs: object) -> None:
    invalid = set(kwargs) - _ALLOWED_COLS
    if invalid:
        raise ValueError(f"Unknown job fields: {invalid}")
    # ... rest of method unchanged
```

---

## GROUP 3 — Code Quality & Architecture

### 3.1 — `engine.py`: Extract prompt building into its own method
`_generate_chapter()` is 60+ lines with an inline f-string prompt. Extract to `_build_prompt(chapter, subject, rag_ctx, web_ctx, subject_type, format_hint, diff_hint) -> str`. This makes the method testable and the prompt easier to iterate on.

### 3.2 — `web.py`: Move inline HTML to a separate file or use Jinja2
`web.py` contains ~800 lines of inline HTML/CSS/JS in the `_HTML` constant. This makes the file 1,200+ lines total and is unmaintainable. Since Jinja2 is already a dependency, move the HTML to `src/studycraft/templates/index.html` and load it with:

```python
from jinja2 import Environment, PackageLoader
env = Environment(loader=PackageLoader("studycraft", "templates"))

@app.get("/", response_class=HTMLResponse)
async def root():
    return env.get_template("index.html").render()
```

Update `pyproject.toml` to include the templates dir in the wheel:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/studycraft"]
include = ["src/studycraft/templates/*"]
```

### 3.3 — `detector.py`: Add LLM-assisted fallback for TOC extraction
When the regex-based chapter detection yields 0 or 1 chapters on a real document (not the window fallback), add an optional LLM call to extract the table of contents. This is already in PLAN.md Phase 4.1. Wire it up:

```python
def detect_chapters(text: str, llm_client=None) -> list[Chapter]:
    chapters = _try_regex_strategies(text)
    if len(chapters) <= 1 and llm_client:
        chapters = _llm_toc_extraction(text[:4000], llm_client) or chapters
    if not chapters:
        chapters = _fixed_window_fallback(text)
    return _filter_backmatter(chapters)
```

Pass `llm_client` from `engine.py`'s `StudyCraft.run()`.

### 3.4 — `model_registry.py`: Add timeout and retry to `fetch_models()`
The current `urllib.request.urlopen(req, timeout=15)` has no retry. Wrap in a simple retry loop (max 2 retries, 2s delay) so the model list command doesn't silently fail on flaky connections:

```python
for attempt in range(3):
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read())
        break
    except (urllib.error.URLError, TimeoutError):
        if attempt == 2:
            raise
        time.sleep(2)
```

### 3.5 — `researcher.py`: Add per-query timeout and cache
DuckDuckGo searches can hang for 10–30s per query, and each chapter runs 4–5 queries. This is the biggest latency sink. Fix:

```python
import functools, hashlib, json
from pathlib import Path

_RESEARCH_CACHE = Path.home() / ".studycraft" / "research_cache.json"
_CACHE_TTL = 3600 * 6  # 6 hours

def _search(query: str, max_results: int) -> str:
    # Check cache
    key = hashlib.md5(query.encode()).hexdigest()
    cache = _load_cache()
    if key in cache and time.time() - cache[key]["ts"] < _CACHE_TTL:
        return cache[key]["result"]

    try:
        from ddgs import DDGS
        hits = DDGS().text(query, max_results=max_results, timeout=8)
        # ... format hits
        result = "\n\n".join(lines)
        _save_cache(key, result)
        return result
    except Exception as exc:
        return ""
```

---

## GROUP 4 — Missing Features (High Priority from PLAN.md)

### 4.1 — Server-Sent Events (SSE) for real-time progress
PLAN.md Phase 2.1 is incomplete. The web UI polls `/api/status/{job_id}` every 2 seconds. Replace with SSE:

```python
from fastapi.responses import StreamingResponse

@app.get("/api/stream/{job_id}")
async def stream_status(job_id: str):
    async def event_generator():
        while True:
            job = _store.get(job_id)
            if not job:
                break
            data = json.dumps(job)
            yield f"data: {data}\n\n"
            if job["status"] in ("done", "error", "stopped"):
                break
            await asyncio.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

Update the frontend JS to use `EventSource("/api/stream/{jobId}")` instead of `setInterval`.

### 4.2 — `GET /api/jobs` endpoint (already in jobstore, not wired)
`JobStore.list_all()` exists but there's no web endpoint for it. The PLAN.md lists this as missing. Wire it:

```python
@app.get("/api/jobs")
async def list_jobs():
    return _store.list_all()
```

Then add a "History" section to the web UI that fetches and renders this on page load.

### 4.3 — Auth header support for deployment
Add a simple API key check for the web UI when `STUDYCRAFT_WEB_TOKEN` is set in the environment, so the app can be deployed publicly without being an open relay for LLM calls:

```python
from fastapi import Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_bearer = HTTPBearer(auto_error=False)

async def _check_auth(
    creds: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> None:
    token = os.getenv("STUDYCRAFT_WEB_TOKEN")
    if token and (not creds or creds.credentials != token):
        raise HTTPException(status_code=401, detail="Unauthorized")

# Add to routes that trigger generation:
@app.post("/api/generate", dependencies=[Depends(_check_auth)])
```

---

## GROUP 5 — Testing Gaps

### 5.1 — Add `tests/test_engine.py` with mocked LLM
The engine is completely untested. Add a test using `unittest.mock.patch` to mock the OpenAI client and assert the pipeline runs end-to-end without network calls:

```python
from unittest.mock import MagicMock, patch
from studycraft.engine import StudyCraft

def test_run_single_chapter(tmp_path):
    doc = tmp_path / "test.txt"
    doc.write_text("Chapter 1: Intro\nThis is the content of chapter one.")

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "# Chapter 1\n## 1. Learning Objectives\n..."

    with patch("openai.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.chat.completions.create.return_value = mock_response
        craft = StudyCraft(api_key="test-key", output_dir=tmp_path / "out")
        # Should not raise
        craft.run(doc, only_chapter=1)
```

### 5.2 — Add `tests/test_web.py` with FastAPI test client
```python
from fastapi.testclient import TestClient

def test_root_returns_html():
    from studycraft.web import app
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "StudyCraft" in resp.text

def test_status_unknown_job():
    from studycraft.web import app
    client = TestClient(app)
    resp = client.get("/api/status/nonexistent")
    assert resp.status_code == 404
```

### 5.3 — Add `pytest-asyncio` to dev deps and fix async test support
The project will need async tests for SSE. Add to `pyproject.toml`:
```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.25",
    "ruff>=0.4",
    "httpx>=0.27",
]
```

And add `pytest.ini` or `pyproject.toml` config:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

---

## GROUP 6 — Developer Experience

### 6.1 — Add `ruff` config to `pyproject.toml`
Currently `ruff` is in dev deps but has no config. Add:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "S"]
ignore = ["S101", "S603", "B008"]   # allow assert in tests, subprocess, Depends()

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S"]
```

Then run `uv run ruff check src/ --fix` and `uv run ruff format src/` to clean up the codebase.

### 6.2 — Update `PLAN.md` to reflect completed items
Several items in PLAN.md are marked `[ ]` (incomplete) but are already implemented:
- `validator.py` — done ✅ (mark it)
- `--with-answers` flag — done ✅
- SQLite job store — done ✅ (`jobstore.py`)
- `--workers N` flag — done ✅
- GitHub Gist — done ✅ (`gist` command)

Update PLAN.md so the status is accurate.

### 6.3 — Add Windows-specific setup note to README
The project is developed on Windows. Add a setup section:

```markdown
## Windows Setup

```powershell
# Set UTF-8 globally (add to your PowerShell profile)
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# Install deps (CPU-only, no CUDA)
uv sync

# If uv sync removes packages unexpectedly, use --frozen to reinstall from lockfile:
uv sync --frozen

# Setup PDF export (one-time, installs Chromium)
uv run studycraft setup-pdf
```
```

---

## Summary of All Changes

| # | File(s) | Change | Priority |
|---|---------|--------|----------|
| 1.1 | `pyproject.toml` | Add `[tool.uv]` CPU torch override | 🔴 Critical |
| 1.2 | `pyproject.toml` | Fix `openai>=2.32.0` → `>=1.82.0` | 🔴 Critical |
| 1.3 | `pyproject.toml` | Move `playwright` to optional dep | 🟡 High |
| 2.1 | `web.py` | Fix JobStore instantiation to module-level singleton | 🔴 Critical |
| 2.2 | `engine.py` | Wire `on_check_control` in parallel worker path | 🟡 High |
| 2.3 | `rag.py` | Sanitize chunk IDs | 🟡 High |
| 2.4 | `loader.py` | Fix EPUB block-vs-inline tag handling | 🟡 High |
| 2.5 | `engine.py` | Fix answer key section slicing bug | 🟡 High |
| 2.6 | `jobstore.py` | Validate allowed column names in `update()` | 🟠 Medium |
| 3.1 | `engine.py` | Extract `_build_prompt()` method | 🟠 Medium |
| 3.2 | `web.py` | Move inline HTML to `templates/index.html` | 🟠 Medium |
| 3.3 | `detector.py` | Add LLM-assisted TOC fallback | 🟠 Medium |
| 3.4 | `model_registry.py` | Add retry loop to `fetch_models()` | 🟠 Medium |
| 3.5 | `researcher.py` | Add per-query cache + timeout | 🟠 Medium |
| 4.1 | `web.py` | Replace polling with SSE streaming | 🟡 High |
| 4.2 | `web.py` | Wire `GET /api/jobs` endpoint | 🟠 Medium |
| 4.3 | `web.py` | Add `STUDYCRAFT_WEB_TOKEN` auth | 🟠 Medium |
| 5.1 | `tests/test_engine.py` | Mocked end-to-end engine test | 🟡 High |
| 5.2 | `tests/test_web.py` | FastAPI test client tests | 🟡 High |
| 5.3 | `pyproject.toml` | Add `pytest-asyncio` + config | 🟠 Medium |
| 6.1 | `pyproject.toml` | Add `ruff` config + run formatter | 🟠 Medium |
| 6.2 | `PLAN.md` | Mark completed items as done | 🟢 Low |
| 6.3 | `README.md` | Add Windows setup section | 🟢 Low |

---

## Completion Status: ✅ ALL DONE

All 23 items across 6 groups have been implemented, tested, and committed.

**Files modified:**
- `pyproject.toml` (package management, dev deps, ruff config)
- `src/studycraft/web.py` (JobStore singleton, SSE, auth, Jinja2 templates)
- `src/studycraft/engine.py` (control handling, prompt extraction, answer key fix, video var cleanup)
- `src/studycraft/rag.py` (ID sanitization)
- `src/studycraft/loader.py` (EPUB whitespace fix)
- `src/studycraft/jobstore.py` (SQL injection prevention)
- `src/studycraft/detector.py` (LLM TOC fallback, zip strict)
- `src/studycraft/model_registry.py` (retry loop)
- `src/studycraft/researcher.py` (cache + timeout)
- `src/studycraft/templates/index.html` (new, 650+ lines)
- `AGENTS.md` (pdf extra note)
- `README.md` (Windows setup, dependency notes)
- `PLAN.md` (completed item markers)
- `tests/test_engine.py` (new)
- `tests/test_web.py` (new)

**Test results:** 96 passed, 0 failed

---

## Version Bump

**Bumped:** v0.9.0 → **v0.9.1**

**Rationale:** This release contains critical bug fixes (JobStore race condition, parallel worker control, RAG ID sanitization, EPUB parsing, answer key slicing, SQL injection prevention), new features (SSE streaming, auth, LLM TOC fallback, research cache), and developer experience improvements (ruff config, tests). All are backward-compatible improvements; no breaking changes.

---

**End of completed prompt — no further action required.**
