"""
StudyCraft – SQLite job store.

Replaces the in-memory _jobs dict with persistent storage.
Auto-cleans jobs older than 24 hours on startup.
Supports pause/stop control signals.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path


_EXPIRY_SECONDS = 86400  # 24 hours


class JobStore:
    def __init__(self, db_path: str | Path = "output/jobs.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'queued',
                progress INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '',
                files TEXT NOT NULL DEFAULT '{}',
                control TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL
            )"""
        )
        self._conn.commit()
        # Migrate: add control column if missing (existing DBs)
        try:
            self._conn.execute(
                "ALTER TABLE jobs ADD COLUMN control TEXT NOT NULL DEFAULT ''"
            )
            self._conn.commit()
        except sqlite3.OperationalError:
            pass
        self._cleanup()

    def create(self, job_id: str) -> None:
        self._conn.execute(
            "INSERT INTO jobs (id, status, progress, message, files, control, created_at) VALUES (?,?,?,?,?,?,?)",
            (job_id, "queued", 0, "Queued\u2026", "{}", "", time.time()),
        )
        self._conn.commit()

    def update(self, job_id: str, **kwargs: object) -> None:
        if "files" in kwargs and isinstance(kwargs["files"], dict):
            kwargs["files"] = json.dumps(kwargs["files"])
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [job_id]
        self._conn.execute(f"UPDATE jobs SET {sets} WHERE id = ?", vals)  # noqa: S608
        self._conn.commit()

    def get(self, job_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT id, status, progress, message, files, control FROM jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "status": row[1],
            "progress": row[2],
            "message": row[3],
            "files": json.loads(row[4]),
            "control": row[5],
        }

    def get_control(self, job_id: str) -> str:
        """Get the control signal for a job (pause/stop/empty)."""
        row = self._conn.execute(
            "SELECT control FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return row[0] if row else ""

    def list_all(self) -> dict[str, dict]:
        rows = self._conn.execute(
            "SELECT id, status, progress, message FROM jobs ORDER BY created_at DESC"
        ).fetchall()
        return {r[0]: {"status": r[1], "progress": r[2], "message": r[3]} for r in rows}

    def _cleanup(self) -> None:
        cutoff = time.time() - _EXPIRY_SECONDS
        self._conn.execute("DELETE FROM jobs WHERE created_at < ?", (cutoff,))
        self._conn.commit()
