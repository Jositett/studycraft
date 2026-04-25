"""
StudyCraft – Web UI.

Start with:   uv run studycraft-web
Or directly:  uv run python -m studycraft.web
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

# ── Dependency guard ──────────────────────────────────────────────────────────
try:
    from contextlib import asynccontextmanager

    from fastapi import (
        BackgroundTasks,
        Depends,
        FastAPI,
        File,
        Form,
        HTTPException,
        Security,
        UploadFile,
    )
    from fastapi.responses import (
        FileResponse,
        HTMLResponse,
        JSONResponse,
        StreamingResponse,
    )
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

from jinja2 import Environment, PackageLoader, select_autoescape

from .jobstore import JobStore

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Global JobStore instance (initialized on startup)
_store: JobStore | None = None

# ── Optional API key authentication ───────────────────────────────────────────
_bearer = HTTPBearer(auto_error=False)


async def _check_auth(
    creds: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> None:
    token = os.getenv("STUDYCRAFT_WEB_TOKEN")
    if token and (not creds or creds.credentials != token):
        raise HTTPException(status_code=401, detail="Unauthorized")


# ── Template setup via Jinja2 ──────────────────────────────────────────────────
_jinja_env = Environment(
    loader=PackageLoader("studycraft", "templates"),
    autoescape=select_autoescape(["html", "htmxml"]),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize JobStore singleton
    global _store
    _store = JobStore(db_path=OUTPUT_DIR / "jobs.db")
    yield
    # Shutdown: close DB connection
    if _store:
        _store._conn.close()


def create_app() -> FastAPI:  # type: ignore
    if not _FASTAPI_AVAILABLE:
        raise ImportError(
            "Web UI requires extra dependencies. Install with:\n"
            "  uv add fastapi uvicorn jinja2 python-multipart"
        )

    app = FastAPI(title="StudyCraft", version="0.9.2", lifespan=lifespan)

    @app.get("/favicon.svg")
    async def favicon():
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<text y=".9em" font-size="90">\U0001f4d6</text></svg>'
        )
        return HTMLResponse(content=svg, media_type="image/svg+xml")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return _jinja_env.get_template("index.html").render()

    @app.get("/api/config")
    async def config():
        return JSONResponse(
            {
                "has_openrouter": bool(
                    os.getenv("OPENROUTER_API_KEY") or os.getenv("STUDYCRAFT_API_KEY")
                ),
                "has_hf_token": bool(os.getenv("HF_TOKEN")),
                "has_github_token": bool(os.getenv("GITHUB_TOKEN")),
            }
        )

    @app.post("/api/generate", dependencies=[Depends(_check_auth)])
    async def generate(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        subject: str = Form(""),
        model: str = Form("meta-llama/llama-3.1-8b-instruct:free"),
        with_answers: str = Form(""),
        with_audio: str = Form(""),
        with_video: str = Form(""),
        theme: str = Form("dark"),
        difficulty: str = Form("intermediate"),
        api_key: str = Form(""),
        hf_token: str = Form(""),
        github_token: str = Form(""),
        context_files: list[UploadFile] = File(default=[]),
    ):
        # BYOK: user-provided key overrides server env
        effective_key = (
            api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("STUDYCRAFT_API_KEY")
        )
        if not effective_key:
            raise HTTPException(
                status_code=400,
                detail="OpenRouter API key is required. Add it in the API Keys section above.",
            )
        # Resolve checkbox values safely — bool('0') and bool('false') would be True
        _truthy = ("1", "true", "yes")
        do_answers = with_answers.strip().lower() in _truthy
        do_audio = with_audio.strip().lower() in _truthy
        do_video = with_video.strip().lower() in _truthy

        # Capture optional tokens for this job without polluting the global env
        effective_hf = hf_token or os.getenv("HF_TOKEN", "")
        effective_github = github_token or os.getenv("GITHUB_TOKEN", "")

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

        _store.create(job_id)
        background_tasks.add_task(
            _run_job,
            job_id,
            save_path,
            subject or None,
            model,
            effective_key,
            do_answers,
            do_audio,
            do_video,
            ctx_paths,
            _store,
            theme,
            difficulty,
        )
        return JSONResponse({"job_id": job_id})

    @app.get("/api/status/{job_id}")
    async def status(job_id: str):
        job = _store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return JSONResponse(job)

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

    @app.get("/api/models")
    async def list_models(refresh: bool = False, user_key: str = ""):
        from .model_registry import _HEALTH_FILE, fetch_models, get_verified_free_models

        models = fetch_models(force=refresh)

        # On refresh, also run 1-token health probes
        if refresh:
            api_key = user_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("STUDYCRAFT_API_KEY")
            if api_key:
                get_verified_free_models(api_key, force=True)

        # Load health cache to filter out known-bad models
        healthy_ids = None
        if _HEALTH_FILE.exists():
            try:
                import json as _json

                hdata = _json.loads(_HEALTH_FILE.read_text(encoding="utf-8"))
                healthy_ids = set(hdata.get("healthy", []))
            except Exception:
                pass

        free = [m for m in models if m["is_free"]]
        paid = [m for m in models if not m["is_free"]]

        if healthy_ids:
            healthy_free = [m for m in free if m["id"] in healthy_ids]
            other_free = [m for m in free if m["id"] not in healthy_ids]
            healthy_free.sort(key=lambda m: m["context_length"], reverse=True)
            other_free.sort(key=lambda m: m["context_length"], reverse=True)
            free = healthy_free + other_free
        else:
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
                    "healthy": m["id"] in healthy_ids if healthy_ids else None,
                }
                for m in result
            ]
        )

    @app.get("/api/jobs")
    async def list_jobs():
        return JSONResponse(_store.list_all())

    @app.post("/api/models/test")
    async def test_models(user_key: str = Form("")):
        from .model_registry import get_verified_free_models

        api_key = user_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("STUDYCRAFT_API_KEY")
        if not api_key:
            raise HTTPException(status_code=400, detail="OpenRouter API key required")
        verified = get_verified_free_models(api_key, force=True)
        return JSONResponse({"tested": len(verified), "healthy": [m["id"] for m in verified]})

    @app.get("/api/download/{job_id}/{fmt}")
    async def download(job_id: str, fmt: str):
        job = _store.get(job_id)
        if not job or fmt not in job.get("files", {}):
            raise HTTPException(status_code=404, detail="File not found")
        file_path = job["files"][fmt]
        return FileResponse(file_path, filename=Path(file_path).name)

    @app.post("/api/control/{job_id}")
    async def control(job_id: str, action: str = Form(...)):
        job = _store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if action in ("pause", "stop", "resume"):
            ctrl = "" if action == "resume" else action
            _store.update(job_id, control=ctrl)
            return JSONResponse({"ok": True, "action": action})
        raise HTTPException(status_code=400, detail="Invalid action")

    return app


async def _run_job(
    job_id: str,
    doc_path: Path,
    subject: str | None,
    model: str,
    api_key: str,
    with_answers: bool = False,
    with_audio: bool = False,
    with_video: bool = False,
    context_files: list[str] | None = None,
    store: object | None = None,
    theme: str = "dark",
    difficulty: str = "intermediate",
):
    """Background job that runs StudyCraft and updates the job store."""
    try:
        store.update(job_id, status="running", progress=5, message="Loading document\u2026")

        from .engine import StudyCraft

        def _on_progress(current: int, total: int, msg: str) -> None:
            pct = int(10 + (current / max(total, 1)) * 85)
            store.update(job_id, progress=pct, message=msg)

        def _check_control() -> str | None:
            """Check for pause/stop signals. Returns 'stop' or blocks on pause."""
            ctrl = store.get_control(job_id)
            if ctrl == "stop":
                return "stop"
            while ctrl == "pause":
                store.update(job_id, message="Paused")
                import time as _time

                _time.sleep(2)
                ctrl = store.get_control(job_id)
                if ctrl == "stop":
                    return "stop"
            return None

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
            with_audio=with_audio,
            with_video=with_video,
            context_files=context_files,
            theme=theme,
            on_check_control=_check_control,
            difficulty=difficulty,
        )

        # Check if stopped during generation
        if store.get_control(job_id) == "stop":
            flat_stopped: dict[str, str] = {}
            for fmt, path in paths.items():
                if isinstance(path, dict):
                    dirs = {str(p.parent) for p in path.values() if isinstance(p, Path)}
                    if dirs:
                        flat_stopped[fmt] = dirs.pop()
                else:
                    flat_stopped[fmt] = str(path)
            store.update(
                job_id,
                status="stopped",
                message="Stopped by user",
                files=flat_stopped,
            )
            return

        # Flatten paths: audio/video are dicts of {ch_num: Path}, store as dir path
        flat: dict[str, str] = {}
        for fmt, path in paths.items():
            if isinstance(path, dict):
                # Store the parent directory for audio/video
                dirs = {str(p.parent) for p in path.values() if isinstance(p, Path)}
                if dirs:
                    flat[fmt] = dirs.pop()
            else:
                flat[fmt] = str(path)

        store.update(
            job_id,
            status="done",
            progress=100,
            message="Guide ready!",
            files=flat,
        )
    except Exception as exc:
        store.update(job_id, status="error", message=str(exc))


def main():
    """Entry point for `studycraft-web` command."""
    try:
        import uvicorn  # type: ignore
    except ImportError:
        print("Install web dependencies first:\n  uv add fastapi uvicorn python-multipart")
        sys.exit(1)

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    args = parser.parse_args()

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=args.port, reload=False)


if __name__ == "__main__":
    main()
