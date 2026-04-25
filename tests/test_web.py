"""Tests for StudyCraft web UI."""

from studycraft.web import create_app


def test_root_returns_html():
    """Root page should return HTML containing 'StudyCraft'."""
    app = create_app()
    from fastapi.testclient import TestClient

    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "StudyCraft" in resp.text


def test_status_unknown_job():
    """Status endpoint for unknown job should return 404."""
    app = create_app()
    from fastapi.testclient import TestClient

    client = TestClient(app)
    resp = client.get("/api/status/nonexistent")
    assert resp.status_code == 404


def test_list_jobs_empty():
    """Jobs list should return empty object initially."""
    app = create_app()
    from fastapi.testclient import TestClient

    client = TestClient(app)
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
