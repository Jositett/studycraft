"""
StudyCraft – Web UI (Phase 2 scaffold).

Start with:   uv run studycraft-web
Or directly:  uv run python -m studycraft.web

Requires additional dependencies (not in base install):
    uv add fastapi uvicorn jinja2 python-multipart

This file is a complete, working scaffold. Phase 2 tasks are marked TODO.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

# ── Dependency guard ──────────────────────────────────────────────────────────
try:
    from fastapi import FastAPI, File, Form, UploadFile, BackgroundTasks, HTTPException
    from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False


UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# In-memory job tracker: job_id → {status, progress, files}
_jobs: dict[str, dict] = {}


# ── Inline HTML UI (no templates dir needed) ──────────────────────────────────
_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>StudyCraft — Practice Guide Generator</title>
<style>
  :root {
    --primary: #2563eb; --accent: #7c3aed;
    --bg: #f9fafb; --surface: #fff; --border: #e5e7eb;
    --text: #111827; --muted: #6b7280;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }

  header {
    background: linear-gradient(135deg, var(--primary), var(--accent));
    color: white; padding: 1.5rem 2rem; text-align: center;
  }
  header h1 { font-size: 1.8rem; font-weight: 800; }
  header p { opacity: .8; margin-top: .25rem; }

  main { max-width: 720px; margin: 2.5rem auto; padding: 0 1.5rem; }

  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 2rem; margin-bottom: 1.5rem;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
  }
  .card h2 { font-size: 1.1rem; font-weight: 700; margin-bottom: 1.25rem; color: var(--primary); }

  label { display: block; font-size: .9rem; font-weight: 600; margin-bottom: .35rem; }
  input[type=text], select {
    width: 100%; padding: .6rem .9rem; border: 1px solid var(--border);
    border-radius: 8px; font-size: .95rem; margin-bottom: 1rem;
    outline: none; transition: border .2s;
  }
  input:focus, select:focus { border-color: var(--primary); }

  .drop-zone {
    border: 2px dashed var(--border); border-radius: 10px;
    padding: 2.5rem; text-align: center; cursor: pointer;
    transition: border-color .2s, background .2s; margin-bottom: 1rem;
  }
  .drop-zone:hover, .drop-zone.active { border-color: var(--primary); background: #eff6ff; }
  .drop-zone p { color: var(--muted); font-size: .9rem; margin-top: .5rem; }
  .drop-zone input { display: none; }
  .file-name { color: var(--primary); font-weight: 600; margin-top: .5rem; font-size: .9rem; }

  button[type=submit] {
    width: 100%; padding: .85rem; background: var(--primary); color: white;
    border: none; border-radius: 8px; font-size: 1rem; font-weight: 700;
    cursor: pointer; transition: background .2s;
  }
  button[type=submit]:hover { background: #1d4ed8; }
  button[type=submit]:disabled { background: var(--muted); cursor: not-allowed; }

  .progress-card { display: none; }
  .progress-bar-wrap {
    height: 8px; background: var(--border); border-radius: 99px; overflow: hidden; margin: 1rem 0;
  }
  .progress-bar { height: 100%; background: var(--primary); width: 0%; transition: width .4s; }
  .status-text { font-size: .9rem; color: var(--muted); }

  .results { display: none; }
  .dl-btn {
    display: inline-block; padding: .55rem 1.2rem; border-radius: 8px;
    font-size: .9rem; font-weight: 600; text-decoration: none; margin-right: .5rem; margin-top: .5rem;
  }
  .dl-md   { background: #f1f5f9; color: var(--text); border: 1px solid var(--border); }
  .dl-html { background: #eff6ff; color: var(--primary); border: 1px solid var(--primary); }
  .dl-pdf  { background: var(--accent); color: white; }

  .error { color: #dc2626; background: #fef2f2; border: 1px solid #fecaca;
           border-radius: 8px; padding: .75rem 1rem; margin-top: 1rem; font-size: .9rem; }

  footer { text-align: center; color: var(--muted); font-size: .8rem; padding: 2rem; }
</style>
</head>
<body>

<header>
  <h1>📖 StudyCraft</h1>
  <p>Craft structured, research-backed practice guides from any document</p>
</header>

<main>
  <div class="card" id="upload-card">
    <h2>Generate a Practice Guide</h2>

    <div class="drop-zone" id="drop-zone">
      <svg width="40" height="40" fill="none" stroke="#9ca3af" stroke-width="1.5" viewBox="0 0 24 24">
        <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1M12 12V4m0 0l-3 3m3-3l3 3" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <p>Drag & drop your document here, or <strong>click to browse</strong></p>
      <p>PDF · DOCX · TXT · MD · RTF</p>
      <input type="file" id="file-input" accept=".pdf,.docx,.txt,.md,.rtf">
      <div class="file-name" id="file-name"></div>
    </div>

    <label for="subject-input">Subject name (optional — auto-detected if blank)</label>
    <input type="text" id="subject-input" placeholder="e.g. Advanced Java, Calculus II, History of Art">

    <label for="answers-check" style="display:inline-flex;align-items:center;gap:.5rem;margin-bottom:1rem;cursor:pointer">
      <input type="checkbox" id="answers-check" style="width:1.1rem;height:1.1rem">
      Generate answer key
    </label>

    <label for="model-select">Model</label>
    <select id="model-select">
      <option value="meta-llama/llama-3.1-8b-instruct:free">Llama 3.1 8B (Free · Fast)</option>
      <option value="meta-llama/llama-3.3-70b-instruct:free">Llama 3.3 70B (Free · Better quality)</option>
      <option value="mistralai/mistral-7b-instruct:free">Mistral 7B (Free · Alternate)</option>
      <option value="google/gemma-3-27b-it:free">Gemma 3 27B (Free · Good)</option>
      <option value="anthropic/claude-3-5-haiku">Claude 3.5 Haiku (Paid · Excellent)</option>
      <option value="openai/gpt-4o-mini">GPT-4o Mini (Paid · Very good)</option>
    </select>

    <button type="submit" id="generate-btn" onclick="startGeneration()">Generate Guide</button>
    <div class="error" id="error-msg" style="display:none"></div>
  </div>

  <div class="card progress-card" id="progress-card">
    <h2>⚙ Generating your guide…</h2>
    <div class="progress-bar-wrap"><div class="progress-bar" id="progress-bar"></div></div>
    <div class="status-text" id="status-text">Starting up…</div>
  </div>

  <div class="card results" id="results-card">
    <h2>✅ Guide Ready!</h2>
    <p style="color:#6b7280;margin-bottom:1rem">Download your practice guide in your preferred format:</p>
    <div id="download-links"></div>
  </div>
</main>

<footer>StudyCraft · AI-powered practice guides · <a href="/docs">API docs</a></footer>

<script>
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');
  const fileName  = document.getElementById('file-name');
  let selectedFile = null;

  dropZone.addEventListener('click', () => fileInput.click());
  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('active'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('active'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault(); dropZone.classList.remove('active');
    selectedFile = e.dataTransfer.files[0];
    fileName.textContent = selectedFile.name;
  });
  fileInput.addEventListener('change', () => {
    selectedFile = fileInput.files[0];
    fileName.textContent = selectedFile ? selectedFile.name : '';
  });

  async function startGeneration() {
    const errEl = document.getElementById('error-msg');
    errEl.style.display = 'none';

    if (!selectedFile) {
      errEl.textContent = 'Please select a document first.';
      errEl.style.display = 'block';
      return;
    }

    const btn = document.getElementById('generate-btn');
    btn.disabled = true;
    document.getElementById('upload-card').style.opacity = '.5';
    document.getElementById('progress-card').style.display = 'block';

    const form = new FormData();
    form.append('file', selectedFile);
    form.append('subject', document.getElementById('subject-input').value);
    form.append('model', document.getElementById('model-select').value);
    form.append('with_answers', document.getElementById('answers-check').checked ? '1' : '');

    let jobId;
    try {
      const res = await fetch('/api/generate', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');
      jobId = data.job_id;
    } catch(e) {
      errEl.textContent = e.message;
      errEl.style.display = 'block';
      btn.disabled = false;
      document.getElementById('upload-card').style.opacity = '1';
      document.getElementById('progress-card').style.display = 'none';
      return;
    }

    // Poll status
    const poll = setInterval(async () => {
      const r = await fetch(`/api/status/${jobId}`);
      const d = await r.json();
      document.getElementById('status-text').textContent = d.message || '';
      document.getElementById('progress-bar').style.width = (d.progress || 0) + '%';

      if (d.status === 'done') {
        clearInterval(poll);
        showResults(jobId, d.files);
      } else if (d.status === 'error') {
        clearInterval(poll);
        errEl.textContent = d.message;
        errEl.style.display = 'block';
        btn.disabled = false;
        document.getElementById('upload-card').style.opacity = '1';
      }
    }, 2000);
  }

  function showResults(jobId, files) {
    document.getElementById('progress-card').style.display = 'none';
    document.getElementById('results-card').style.display = 'block';
    const links = document.getElementById('download-links');
    links.innerHTML = '';
    for (const [fmt, path] of Object.entries(files)) {
      const cls = fmt === 'pdf' ? 'dl-pdf' : fmt === 'html' ? 'dl-html' : 'dl-md';
      links.innerHTML += `<a class="dl-btn ${cls}" href="/api/download/${jobId}/${fmt}" download>
        Download ${fmt.toUpperCase()}
      </a>`;
    }
  }
</script>
</body>
</html>
"""


def create_app() -> "FastAPI":  # type: ignore
    if not _FASTAPI_AVAILABLE:
        raise ImportError(
            "Web UI requires extra dependencies. Install with:\n"
            "  uv add fastapi uvicorn jinja2 python-multipart"
        )

    app = FastAPI(title="StudyCraft", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return _HTML

    @app.post("/api/generate")
    async def generate(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        subject: str = Form(""),
        model: str = Form("meta-llama/llama-3.1-8b-instruct:free"),
        with_answers: str = Form(""),
    ):
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("STUDYCRAFT_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500, detail="OPENROUTER_API_KEY not configured on server"
            )

        job_id = str(uuid.uuid4())[:8]
        suffix = Path(file.filename or "doc.pdf").suffix.lower()
        save_path = UPLOAD_DIR / f"{job_id}{suffix}"

        content = await file.read()
        save_path.write_bytes(content)

        _jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            "message": "Queued…",
            "files": {},
        }
        background_tasks.add_task(
            _run_job, job_id, save_path, subject or None, model, api_key, bool(with_answers)
        )
        return JSONResponse({"job_id": job_id})

    @app.get("/api/status/{job_id}")
    async def status(job_id: str):
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return JSONResponse(job)

    @app.get("/api/jobs")
    async def list_jobs():
        """List all jobs with their status."""
        return JSONResponse({
            jid: {"status": j["status"], "progress": j["progress"], "message": j["message"]}
            for jid, j in _jobs.items()
        })

    @app.get("/api/download/{job_id}/{fmt}")
    async def download(job_id: str, fmt: str):
        job = _jobs.get(job_id)
        if not job or fmt not in job.get("files", {}):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(job["files"][fmt])

    return app


async def _run_job(
    job_id: str, doc_path: Path, subject: str | None, model: str, api_key: str,
    with_answers: bool = False,
):
    """Background job that runs StudyCraft and updates _jobs[job_id]."""
    try:
        _jobs[job_id].update(status="running", progress=5, message="Loading document…")

        from .engine import StudyCraft

        def _on_progress(current: int, total: int, msg: str) -> None:
            pct = int(10 + (current / max(total, 1)) * 85)  # 10–95%
            _jobs[job_id].update(progress=pct, message=msg)

        craft = StudyCraft(
            api_key=api_key,
            model=model,
            output_dir=str(OUTPUT_DIR / job_id),
        )

        paths = craft.run(
            document_path=doc_path, subject=subject, on_progress=_on_progress,
            with_answers=with_answers,
        )

        _jobs[job_id].update(
            status="done",
            progress=100,
            message="Guide ready!",
            files={fmt: str(path) for fmt, path in paths.items()},
        )
    except Exception as exc:
        _jobs[job_id].update(status="error", message=str(exc))


def main():
    """Entry point for `studycraft-web` command."""
    try:
        import uvicorn  # type: ignore
    except ImportError:
        print(
            "Install web dependencies first:\n  uv add fastapi uvicorn python-multipart"
        )
        sys.exit(1)

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
