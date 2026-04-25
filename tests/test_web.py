"""Tests for StudyCraft web UI with filesystem isolation."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def test_root_returns_html(monkeypatch, tmp_path: Path):
    """Root page should return HTML containing 'StudyCraft'."""
    from studycraft import web as web_mod

    # Isolate filesystem: redirect OUTPUT_DIR and UPLOAD_DIR to tmp_path
    fake_output = tmp_path / "out"
    fake_upload = tmp_path / "uploads"
    monkeypatch.setattr(web_mod, "OUTPUT_DIR", fake_output)
    monkeypatch.setattr(web_mod, "UPLOAD_DIR", fake_upload)

    # Mock JobStore to avoid real DB creation
    mock_store = MagicMock()
    mock_store.get.return_value = None
    mock_store.list_all.return_value = {}
    monkeypatch.setattr(web_mod, "_store", mock_store, raising=False)

    # Patch JobStore class so startup event creates the mock
    monkeypatch.setattr(web_mod, "JobStore", lambda db_path=None: mock_store)

    with TestClient(web_mod.create_app()) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "StudyCraft" in resp.text


def test_status_unknown_job(monkeypatch, tmp_path: Path):
    """Status endpoint for unknown job should return 404."""
    from studycraft import web as web_mod

    fake_output = tmp_path / "out"
    fake_upload = tmp_path / "uploads"
    monkeypatch.setattr(web_mod, "OUTPUT_DIR", fake_output)
    monkeypatch.setattr(web_mod, "UPLOAD_DIR", fake_upload)

    mock_store = MagicMock()
    mock_store.get.return_value = None
    monkeypatch.setattr(web_mod, "_store", mock_store, raising=False)
    monkeypatch.setattr(web_mod, "JobStore", lambda db_path=None: mock_store)

    with TestClient(web_mod.create_app()) as client:
        resp = client.get("/api/status/nonexistent")
        assert resp.status_code == 404


def test_list_jobs_empty(monkeypatch, tmp_path: Path):
    """Jobs list should return empty dict initially."""
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
        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert len(data) == 0  # Should be empty
