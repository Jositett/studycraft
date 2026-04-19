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


# ── Inline HTML UI (no templates dir needed) ──────────────────────────────────
_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>StudyCraft — Practice Guide Generator</title>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<style>
  :root {
    --primary: #6d9fff; --primary-hover: #5a8af2; --accent: #a78bfa;
    --bg: #0f1117; --surface: #1a1d2e; --surface-hover: #222640;
    --border: #2a2f45; --border-hover: #3d4463;
    --text: #e2e8f0; --muted: #8892b0;
    --success: #4ade80; --error-bg: #2d1b1b; --error-border: #7f1d1d; --error-text: #fca5a5;
    --radius: 12px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }

  header {
    background: linear-gradient(135deg, #1e2540 0%, #0f1117 100%);
    border-bottom: 1px solid var(--border);
    color: white; padding: 2rem 2rem 1.75rem; text-align: center;
  }
  header h1 { font-size: 2rem; font-weight: 800; letter-spacing: -.02em; }
  header h1 span { background: linear-gradient(135deg, var(--primary), var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  header p { color: var(--muted); margin-top: .4rem; font-size: .95rem; }

  main { max-width: 680px; margin: 2rem auto; padding: 0 1.25rem; }

  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 1.75rem; margin-bottom: 1.25rem;
    transition: border-color .2s;
  }
  .card:hover { border-color: var(--border-hover); }
  .card h2 { font-size: 1rem; font-weight: 700; margin-bottom: 1.25rem; color: var(--primary); letter-spacing: -.01em; }

  label { display: block; font-size: .85rem; font-weight: 600; margin-bottom: .35rem; color: var(--muted); }
  input[type=text], select {
    width: 100%; padding: .6rem .85rem; border: 1px solid var(--border);
    border-radius: 8px; font-size: .9rem; margin-bottom: 1rem;
    outline: none; transition: border-color .2s, box-shadow .2s;
    background: var(--bg); color: var(--text);
  }
  select option { background: var(--surface); color: var(--text); }
  input:focus, select:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(109,159,255,.15); }
  input::placeholder { color: var(--muted); opacity: .6; }

  .drop-zone {
    border: 2px dashed var(--border); border-radius: var(--radius);
    padding: 2.25rem 1.5rem; text-align: center; cursor: pointer;
    transition: border-color .2s, background .2s; margin-bottom: 1.25rem;
  }
  .drop-zone:hover, .drop-zone.active { border-color: var(--primary); background: rgba(109,159,255,.06); }
  .drop-zone.has-file { border-color: var(--success); border-style: solid; background: rgba(74,222,128,.05); }
  .drop-zone p { color: var(--muted); font-size: .85rem; margin-top: .5rem; }
  .drop-zone p strong { color: var(--primary); }
  .drop-zone .formats { font-size: .75rem; opacity: .6; margin-top: .25rem; }
  .drop-zone input { display: none; }
  .file-name { color: var(--success); font-weight: 600; margin-top: .5rem; font-size: .9rem; }

  .checkbox-row {
    display: inline-flex; align-items: center; gap: .5rem;
    margin-bottom: 1rem; cursor: pointer; font-size: .9rem;
  }
  .checkbox-row input[type=checkbox] {
    width: 1.1rem; height: 1.1rem; accent-color: var(--primary); cursor: pointer;
  }

  .context-hint { color: var(--muted); font-size: .75rem; margin: -.5rem 0 1rem; opacity: .7; }

  button[type=submit] {
    width: 100%; padding: .85rem; font-size: 1rem; font-weight: 700;
    border: none; border-radius: 8px; cursor: pointer;
    background: linear-gradient(135deg, var(--primary), var(--accent));
    color: #fff; transition: opacity .2s, transform .1s;
  }
  button[type=submit]:hover { opacity: .9; }
  button[type=submit]:active { transform: scale(.99); }
  button[type=submit]:disabled { opacity: .4; cursor: not-allowed; transform: none; }

  .progress-card { display: none; }
  .progress-bar-wrap {
    height: 6px; background: var(--border); border-radius: 99px; overflow: hidden; margin: 1rem 0;
  }
  .progress-bar {
    height: 100%; width: 0%; border-radius: 99px;
    background: linear-gradient(90deg, var(--primary), var(--accent));
    transition: width .5s ease;
  }
  .status-text { font-size: .85rem; color: var(--muted); }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .5; } }
  .status-text.running { animation: pulse 2s ease-in-out infinite; }

  .results { display: none; }
  .dl-grid { display: flex; flex-wrap: wrap; gap: .5rem; }
  .dl-btn {
    display: inline-flex; align-items: center; gap: .4rem;
    padding: .55rem 1.1rem; border-radius: 8px;
    font-size: .85rem; font-weight: 600; text-decoration: none;
    transition: opacity .2s, transform .1s; border: 1px solid var(--border);
    background: var(--surface-hover); color: var(--text);
  }
  .dl-btn:hover { opacity: .85; transform: translateY(-1px); }
  .dl-pdf  { background: var(--accent); color: #fff; border-color: var(--accent); }
  .dl-html { background: rgba(109,159,255,.15); color: var(--primary); border-color: var(--primary); }

  .error {
    color: var(--error-text); background: var(--error-bg); border: 1px solid var(--error-border);
    border-radius: 8px; padding: .75rem 1rem; margin-top: 1rem; font-size: .85rem;
  }

  .new-btn {
    display: inline-block; margin-top: 1rem; padding: .5rem 1rem;
    border-radius: 8px; font-size: .85rem; font-weight: 600;
    cursor: pointer; border: 1px solid var(--border); background: var(--bg); color: var(--muted);
    transition: border-color .2s;
  }
  .new-btn:hover { border-color: var(--primary); color: var(--primary); }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 8px; height: 8px; }
  ::-webkit-scrollbar-track { background: var(--bg); }
  ::-webkit-scrollbar-thumb { background: var(--border-hover); border-radius: 4px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--muted); }
  html { scrollbar-color: var(--border-hover) var(--bg); scrollbar-width: thin; }

  /* Layout with aside */
  .page-layout { display: flex; gap: 1.5rem; max-width: 1060px; margin: 2rem auto; padding: 0 1.25rem; align-items: flex-start; }
  main { flex: 1; min-width: 0; margin: 0; padding: 0; max-width: none; }
  aside {
    width: 300px; flex-shrink: 0; position: sticky; top: 1.5rem;
    background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 1.25rem; font-size: .8rem; color: var(--muted); line-height: 1.6;
    max-height: calc(100vh - 3rem); overflow-y: auto;
  }
  aside h3 { color: var(--primary); font-size: .85rem; font-weight: 700; margin-bottom: .75rem; }
  aside h4 { color: var(--text); font-size: .78rem; font-weight: 600; margin: .9rem 0 .3rem; }
  aside p { margin-bottom: .5rem; }
  aside ul { padding-left: 1rem; margin-bottom: .5rem; }
  aside li { margin-bottom: .25rem; }
  aside code { background: var(--bg); padding: .1rem .35rem; border-radius: 4px; font-size: .75rem; }
  aside hr { border: none; border-top: 1px solid var(--border); margin: .75rem 0; }

  @media (max-width: 860px) {
    .page-layout { flex-direction: column; }
    aside { width: 100%; position: static; max-height: none; }
  }

  footer { text-align: center; color: var(--muted); font-size: .75rem; padding: 2rem; opacity: .6; }
  footer a { color: var(--primary); text-decoration: none; }
</style>
</head>
<body>

<header>
  <h1>📖 <span>StudyCraft</span></h1>
  <p>Craft structured, research-backed practice guides from any document</p>
</header>

<div class="page-layout">
<main>
  <div class="card" id="upload-card">
    <h2>Generate a Practice Guide</h2>

    <div class="drop-zone" id="drop-zone">
      <svg width="40" height="40" fill="none" stroke="#9ca3af" stroke-width="1.5" viewBox="0 0 24 24">
        <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1M12 12V4m0 0l-3 3m3-3l3 3" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <p>Drag & drop your document here, or <strong>click to browse</strong></p>
      <p>PDF · DOCX · TXT · MD · RTF · EPUB</p>
      <input type="file" id="file-input" accept=".pdf,.docx,.txt,.md,.rtf,.epub">
      <div class="file-name" id="file-name"></div>
    </div>

    <label for="subject-input">Subject name (optional — auto-detected if blank)</label>
    <input type="text" id="subject-input" placeholder="e.g. Advanced Java, Calculus II, History of Art">

    <label for="answers-check" class="checkbox-row">
      <input type="checkbox" id="answers-check">
      Generate answer key
    </label>

    <label for="context-input">Additional context files (optional)</label>
    <input type="file" id="context-input" multiple accept=".pdf,.docx,.txt,.md,.rtf,.epub"
      style="margin-bottom:.75rem;font-size:.85rem;color:var(--muted)">
    <p class="context-hint">Extra files indexed into RAG for richer context (not generated as chapters)</p>

    <label for="model-select">Model</label>
    <div style="display:flex;gap:.5rem;margin-bottom:1rem">
      <select id="model-select" style="margin-bottom:0;flex:1">
        <option value="" disabled selected>Loading models…</option>
      </select>
      <button type="button" id="refresh-models-btn" onclick="refreshModels()" title="Refresh models" style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:.4rem .6rem;cursor:pointer;color:var(--muted);transition:border-color .2s,color .2s;display:flex;align-items:center">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M23 4v6h-6M1 20v-6h6" stroke-linecap="round" stroke-linejoin="round"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
    </div>

    <label for="theme-select">Theme</label>
    <select id="theme-select">
      <option value="dark">Dark</option>
      <option value="light">Light</option>
      <option value="nord">Nord</option>
      <option value="solarized">Solarized</option>
      <option value="dracula">Dracula</option>
      <option value="github">GitHub</option>
      <option value="monokai">Monokai</option>
      <option value="ocean">Ocean</option>
      <option value="rose-pine">Ros\u00e9 Pine</option>
    </select>

    <button type="submit" id="generate-btn" onclick="startGeneration()">Generate Guide</button>
    <div class="error" id="error-msg" style="display:none"></div>
  </div>

  <div class="card progress-card" id="progress-card">
    <h2>⚙️ Generating your guide…</h2>
    <div class="progress-bar-wrap"><div class="progress-bar" id="progress-bar"></div></div>
    <div class="status-text running" id="status-text">Starting up…</div>
  </div>

  <div class="card results" id="results-card">
    <h2>✅ Guide Ready!</h2>
    <p style="color:var(--muted);margin-bottom:1rem;font-size:.9rem">Download your practice guide:</p>
    <div class="dl-grid" id="download-links"></div>
    <button class="new-btn" onclick="resetUI()">Generate another</button>
  </div>
</main>

<aside>
  <h3>📘 Usage Guide</h3>

  <h4>📄 Upload Document</h4>
  <p>Drag & drop or click to select your source file. Supported formats:</p>
  <ul>
    <li><code>PDF</code> — textbooks, papers, slides</li>
    <li><code>DOCX</code> — Word documents</li>
    <li><code>EPUB</code> — e-books</li>
    <li><code>TXT</code> / <code>MD</code> — plain text or Markdown</li>
    <li><code>RTF</code> — rich text format</li>
  </ul>

  <hr>
  <h4>✏️ Subject Name</h4>
  <p>Optional. If left blank, StudyCraft auto-detects the subject from your document content.</p>

  <hr>
  <h4>✅ Answer Key</h4>
  <p>When checked, a separate answer key file is generated alongside the practice guide with solutions to all quiz questions.</p>

  <hr>
  <h4>📎 Context Files</h4>
  <p>Add supplementary files (lecture notes, references) that get indexed into RAG for richer, more accurate content. These are <em>not</em> turned into chapters.</p>

  <hr>
  <h4>🤖 Model Selection</h4>
  <p>Choose an AI model from OpenRouter. Free models work well for most documents. Paid models produce higher quality for complex subjects.</p>
  <p>Click the <strong>↻</strong> button to refresh the model list from the API (cached 24h).</p>

  <hr>
  <h4>🎨 Theme</h4>
  <p>Choose a color theme for all exported files (HTML, PDF, DOCX, EPUB). Dark is the default.</p>

  <hr>
  <h4>📥 Output Formats</h4>
  <p>Once generated, download your guide in:</p>
  <ul>
    <li><code>MD</code> — Markdown source</li>
    <li><code>HTML</code> — styled web page</li>
    <li><code>PDF</code> — print-ready document</li>
    <li><code>DOCX</code> — Word format</li>
    <li><code>EPUB</code> — e-reader format</li>
  </ul>

  <hr>
  <h4>💡 Tips</h4>
  <ul>
    <li>Larger documents produce more chapters</li>
    <li>Well-structured docs (with headings) yield better outlines</li>
    <li>Use context files for supplementary material</li>
    <li>Free models have rate limits — generation may take a few minutes</li>
  </ul>
</aside>
</div>

<footer>StudyCraft · AI-powered practice guides · <a href="/docs">API docs</a></footer>

<script>
  async function loadModels(refresh = false) {
    const sel = document.getElementById('model-select');
    sel.innerHTML = '<option value="" disabled selected>Loading models…</option>';
    try {
      const url = refresh ? '/api/models?refresh=1' : '/api/models';
      const r = await fetch(url);
      const models = await r.json();
      sel.innerHTML = '';
      models.forEach((m, i) => {
        const opt = document.createElement('option');
        opt.value = m.id;
        const ctx = m.context_length ? `${Math.round(m.context_length/1000)}k` : '';
        const cost = m.is_free ? 'Free' : 'Paid';
        opt.textContent = `${m.name} (${cost}${ctx ? ' \u00b7 ' + ctx : ''})`;
        if (i === 0) opt.selected = true;
        sel.appendChild(opt);
      });
    } catch(e) {
      sel.innerHTML = '<option value="meta-llama/llama-3.1-8b-instruct:free">Llama 3.1 8B (Free)</option>';
    }
  }
  function refreshModels() {
    const btn = document.getElementById('refresh-models-btn');
    btn.style.color = 'var(--primary)';
    btn.style.borderColor = 'var(--primary)';
    loadModels(true).then(() => { btn.style.color = ''; btn.style.borderColor = ''; });
  }
  loadModels();

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
    dropZone.classList.add('has-file');
  });
  fileInput.addEventListener('change', () => {
    selectedFile = fileInput.files[0];
    fileName.textContent = selectedFile ? selectedFile.name : '';
    dropZone.classList.toggle('has-file', !!selectedFile);
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
    form.append('theme', document.getElementById('theme-select').value);
    form.append('with_answers', document.getElementById('answers-check').checked ? '1' : '');
    const ctxFiles = document.getElementById('context-input').files;
    for (let i = 0; i < ctxFiles.length; i++) form.append('context_files', ctxFiles[i]);

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
    const startTime = Date.now();
    const poll = setInterval(async () => {
      const r = await fetch(`/api/status/${jobId}`);
      const d = await r.json();
      const pct = d.progress || 0;
      document.getElementById('progress-bar').style.width = pct + '%';

      // Time estimate
      let timeInfo = '';
      if (pct > 5) {
        const elapsed = (Date.now() - startTime) / 1000;
        const totalEst = elapsed / (pct / 100);
        const remaining = Math.max(0, Math.round(totalEst - elapsed));
        if (remaining > 60) {
          timeInfo = ` (~${Math.round(remaining/60)}m remaining)`;
        } else if (remaining > 0) {
          timeInfo = ` (~${remaining}s remaining)`;
        }
      }
      document.getElementById('status-text').textContent = (d.message || '') + timeInfo;

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
      const cls = fmt === 'pdf' ? 'dl-pdf' : fmt === 'html' ? 'dl-html' : 'dl-btn';
      links.innerHTML += `<a class="dl-btn ${cls}" href="/api/download/${jobId}/${fmt}" download>⬇ ${fmt.toUpperCase()}</a>`;
    }
  }

  function resetUI() {
    selectedFile = null;
    fileName.textContent = '';
    fileInput.value = '';
    dropZone.classList.remove('has-file');
    document.getElementById('subject-input').value = '';
    document.getElementById('answers-check').checked = false;
    document.getElementById('generate-btn').disabled = false;
    document.getElementById('upload-card').style.opacity = '1';
    document.getElementById('results-card').style.display = 'none';
    document.getElementById('progress-card').style.display = 'none';
    document.getElementById('progress-bar').style.width = '0%';
    document.getElementById('error-msg').style.display = 'none';
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

    from .jobstore import JobStore

    app = FastAPI(title="StudyCraft", version="0.7.0")
    store = JobStore(db_path=OUTPUT_DIR / "jobs.db")

    @app.get("/favicon.svg")
    async def favicon():
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">\U0001f4d6</text></svg>'
        return HTMLResponse(content=svg, media_type="image/svg+xml")

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
        theme: str = Form("dark"),
        context_files: list[UploadFile] = File(default=[]),
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

        # Save context files
        ctx_paths: list[str] = []
        for i, cf in enumerate(context_files):
            if cf.filename:
                cf_suffix = Path(cf.filename).suffix.lower()
                cf_path = UPLOAD_DIR / f"{job_id}_ctx{i}{cf_suffix}"
                cf_path.write_bytes(await cf.read())
                ctx_paths.append(str(cf_path))

        store.create(job_id)
        background_tasks.add_task(
            _run_job,
            job_id,
            save_path,
            subject or None,
            model,
            api_key,
            bool(with_answers),
            ctx_paths,
            store,
            theme,
        )
        return JSONResponse({"job_id": job_id})

    @app.get("/api/status/{job_id}")
    async def status(job_id: str):
        job = store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return JSONResponse(job)

    @app.get("/api/models")
    async def list_models(refresh: bool = False):
        from .model_registry import fetch_models

        models = fetch_models(force=refresh)
        free = [m for m in models if m["is_free"]]
        paid = [m for m in models if not m["is_free"]]
        free.sort(key=lambda m: m["context_length"], reverse=True)
        paid.sort(key=lambda m: m["context_length"], reverse=True)
        result = free[:20] + paid[:10]
        return JSONResponse(
            [
                {
                    "id": m["id"],
                    "name": m["name"],
                    "is_free": m["is_free"],
                    "context_length": m["context_length"],
                }
                for m in result
            ]
        )

    @app.get("/api/jobs")
    async def list_jobs():
        return JSONResponse(store.list_all())

    @app.get("/api/download/{job_id}/{fmt}")
    async def download(job_id: str, fmt: str):
        job = store.get(job_id)
        if not job or fmt not in job.get("files", {}):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(job["files"][fmt])

    return app


async def _run_job(
    job_id: str,
    doc_path: Path,
    subject: str | None,
    model: str,
    api_key: str,
    with_answers: bool = False,
    context_files: list[str] | None = None,
    store: "object | None" = None,
    theme: str = "dark",
):
    """Background job that runs StudyCraft and updates the job store."""
    try:
        store.update(
            job_id, status="running", progress=5, message="Loading document\u2026"
        )

        from .engine import StudyCraft

        def _on_progress(current: int, total: int, msg: str) -> None:
            pct = int(10 + (current / max(total, 1)) * 85)
            store.update(job_id, progress=pct, message=msg)

        craft = StudyCraft(
            api_key=api_key,
            model=model,
            output_dir=str(OUTPUT_DIR / job_id),
        )

        paths = craft.run(
            document_path=doc_path,
            subject=subject,
            on_progress=_on_progress,
            with_answers=with_answers,
            context_files=context_files,
            theme=theme,
        )

        store.update(
            job_id,
            status="done",
            progress=100,
            message="Guide ready!",
            files={fmt: str(path) for fmt, path in paths.items()},
        )
    except Exception as exc:
        store.update(job_id, status="error", message=str(exc))


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
