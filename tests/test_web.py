"""Tests for StudyCraft web UI with filesystem isolation."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def web_client(monkeypatch, tmp_path: Path):
    """Provide a TestClient with isolated filesystem and mocked JobStore."""
    from studycraft import web as web_mod

    fake_output = tmp_path / "out"
    fake_upload = tmp_path / "uploads"
    monkeypatch.setattr(web_mod, "OUTPUT_DIR", fake_output)
    monkeypatch.setattr(web_mod, "UPLOAD_DIR", fake_upload)

    mock_store = MagicMock()
    mock_store.get.return_value = None
    mock_store.list_all.return_value = {}
    monkeypatch.setattr(web_mod, "_store", mock_store, raising=False)
    monkeypatch.setattr(web_mod, "JobStore", lambda db_path=None: mock_store)

    with TestClient(web_mod.create_app()) as client:
        yield client


def test_root_returns_html(web_client):
    """Root page should return HTML containing 'StudyCraft'."""
    resp = web_client.get("/")
    assert resp.status_code == 200
    assert "StudyCraft" in resp.text


def test_status_unknown_job(web_client):
    """Status endpoint for unknown job should return 404."""
    resp = web_client.get("/api/status/nonexistent")
    assert resp.status_code == 404


def test_list_jobs_empty(web_client):
    """Jobs list should return empty dict initially."""
    resp = web_client.get("/api/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert len(data) == 0  # Should be empty
