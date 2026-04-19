"""Tests for studycraft.jobstore."""

from pathlib import Path

from studycraft.jobstore import JobStore


def test_create_and_get(tmp_path: Path):
    store = JobStore(db_path=tmp_path / "test.db")
    store.create("abc123")
    job = store.get("abc123")
    assert job is not None
    assert job["status"] == "queued"
    assert job["progress"] == 0
    assert job["message"] == "Queued\u2026"
    assert job["files"] == {}
    assert job["control"] == ""


def test_update(tmp_path: Path):
    store = JobStore(db_path=tmp_path / "test.db")
    store.create("job1")
    store.update("job1", status="running", progress=50, message="Halfway")
    job = store.get("job1")
    assert job["status"] == "running"
    assert job["progress"] == 50
    assert job["message"] == "Halfway"


def test_update_files(tmp_path: Path):
    store = JobStore(db_path=tmp_path / "test.db")
    store.create("job2")
    store.update("job2", status="done", files={"md": "/out/guide.md", "html": "/out/guide.html"})
    job = store.get("job2")
    assert job["files"]["md"] == "/out/guide.md"
    assert job["files"]["html"] == "/out/guide.html"


def test_get_missing(tmp_path: Path):
    store = JobStore(db_path=tmp_path / "test.db")
    assert store.get("nonexistent") is None


def test_list_all(tmp_path: Path):
    store = JobStore(db_path=tmp_path / "test.db")
    store.create("a")
    store.create("b")
    store.update("a", status="done")
    jobs = store.list_all()
    assert len(jobs) == 2
    assert "a" in jobs
    assert "b" in jobs
    assert jobs["a"]["status"] == "done"
    assert jobs["b"]["status"] == "queued"


def test_get_control_default(tmp_path: Path):
    store = JobStore(db_path=tmp_path / "test.db")
    store.create("j1")
    assert store.get_control("j1") == ""


def test_get_control_missing_job(tmp_path: Path):
    store = JobStore(db_path=tmp_path / "test.db")
    assert store.get_control("nonexistent") == ""


def test_control_pause_stop(tmp_path: Path):
    store = JobStore(db_path=tmp_path / "test.db")
    store.create("j2")
    store.update("j2", control="pause")
    assert store.get_control("j2") == "pause"
    assert store.get("j2")["control"] == "pause"

    store.update("j2", control="stop")
    assert store.get_control("j2") == "stop"

    # Resume clears control
    store.update("j2", control="")
    assert store.get_control("j2") == ""
