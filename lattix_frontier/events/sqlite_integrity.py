"""SQLite-backed integrity ledger for event verification."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class IntegrityStore:
    """Persist event hashes for later integrity checks."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS event_integrity (event_id TEXT PRIMARY KEY, event_hash TEXT NOT NULL)"
            )

    def record(self, event_id: str, event_hash: str) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO event_integrity(event_id, event_hash) VALUES (?, ?)",
                (event_id, event_hash),
            )

    def fetch(self, event_id: str) -> str | None:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT event_hash FROM event_integrity WHERE event_id = ?", (event_id,)
            ).fetchone()
        return None if row is None else str(row[0])
