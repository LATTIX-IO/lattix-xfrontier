"""Shared durable state backend for approvals, events, and token security state."""

from __future__ import annotations

import sqlite3
from threading import Lock

from lattix_frontier.config import get_settings
from lattix_frontier.persistence.sqlite_state import resolve_state_store_path

try:
    import psycopg
except ImportError:  # pragma: no cover - optional at import time in minimal environments.
    psycopg = None  # type: ignore[assignment]


class SharedStateBackend:
    """Database-backed state store using Postgres when available, else SQLite."""

    def __init__(self) -> None:
        settings = get_settings()
        self.database_url = settings.database_url
        self.sqlite_path = resolve_state_store_path()
        self.kind = "postgres" if self.database_url.startswith(("postgresql://", "postgres://")) else "sqlite"
        if self.kind == "postgres" and psycopg is None:
            raise RuntimeError("psycopg is required for shared Postgres-backed state")
        self._lock = Lock()
        self._initialize_schema()

    @property
    def uses_shared_backend(self) -> bool:
        """Return whether this backend uses a shared multi-instance database."""

        return self.kind == "postgres"

    def _connect(self):
        if self.kind == "postgres":
            return psycopg.connect(self.database_url)  # type: ignore[union-attr]
        return sqlite3.connect(self.sqlite_path)

    def _query(self, sql: str) -> str:
        if self.kind == "postgres":
            return sql.replace("?", "%s")
        return sql

    def _initialize_schema(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                classification TEXT NOT NULL,
                task TEXT NOT NULL,
                status TEXT NOT NULL,
                decision TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                event_json TEXT NOT NULL,
                event_hash TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_events_created_at ON events (created_at)",
            """
            CREATE TABLE IF NOT EXISTS replay_cache (
                cache_key TEXT PRIMARY KEY,
                expires_at BIGINT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS revocation_cache (
                token_id TEXT PRIMARY KEY,
                expires_at BIGINT NOT NULL
            )
            """,
        ]
        with self._lock:
            with self._connect() as connection:
                for statement in statements:
                    connection.execute(statement)
                connection.commit()

    def put_approval(
        self,
        approval_id: str,
        created_at_iso: str,
        classification: str,
        task: str,
        status: str,
        decision: str | None,
    ) -> None:
        sql = self._query(
            """
            INSERT INTO approvals(id, created_at, classification, task, status, decision)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                created_at = excluded.created_at,
                classification = excluded.classification,
                task = excluded.task,
                status = excluded.status,
                decision = excluded.decision
            """
        )
        with self._lock:
            with self._connect() as connection:
                connection.execute(sql, (approval_id, created_at_iso, classification, task, status, decision))
                connection.commit()

    def get_approval(self, approval_id: str) -> tuple[str, str, str, str, str, str | None] | None:
        sql = self._query(
            """
            SELECT id, created_at, classification, task, status, decision
            FROM approvals
            WHERE id = ?
            """
        )
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(sql, (approval_id,)).fetchone()
        return None if row is None else tuple(row)

    def put_event(self, event_id: str, created_at_iso: str, event_json: str, event_hash: str) -> None:
        sql = self._query(
            """
            INSERT INTO events(event_id, created_at, event_json, event_hash)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (event_id) DO UPDATE SET
                created_at = excluded.created_at,
                event_json = excluded.event_json,
                event_hash = excluded.event_hash
            """
        )
        with self._lock:
            with self._connect() as connection:
                connection.execute(sql, (event_id, created_at_iso, event_json, event_hash))
                connection.commit()

    def list_events(self) -> list[str]:
        sql = self._query("SELECT event_json FROM events ORDER BY created_at ASC")
        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(sql).fetchall()
        return [str(row[0]) for row in rows]

    def get_last_event_hash(self) -> str:
        sql = self._query("SELECT event_hash FROM events ORDER BY created_at DESC LIMIT 1")
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(sql).fetchone()
        return "genesis" if row is None else str(row[0])

    def put_replay_key(self, cache_key: str, expires_at: int) -> bool:
        select_sql = self._query("SELECT 1 FROM replay_cache WHERE cache_key = ?")
        insert_sql = self._query("INSERT INTO replay_cache(cache_key, expires_at) VALUES (?, ?)")
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(select_sql, (cache_key,)).fetchone()
                if row is not None:
                    return False
                connection.execute(insert_sql, (cache_key, expires_at))
                connection.commit()
                return True

    def delete_expired_replay_keys(self, now: int) -> None:
        sql = self._query("DELETE FROM replay_cache WHERE expires_at <= ?")
        with self._lock:
            with self._connect() as connection:
                connection.execute(sql, (now,))
                connection.commit()

    def revoke_token(self, token_id: str, expires_at: int) -> None:
        sql = self._query(
            """
            INSERT INTO revocation_cache(token_id, expires_at)
            VALUES (?, ?)
            ON CONFLICT (token_id) DO UPDATE SET expires_at = excluded.expires_at
            """
        )
        with self._lock:
            with self._connect() as connection:
                connection.execute(sql, (token_id, expires_at))
                connection.commit()

    def is_token_revoked(self, token_id: str, now: int) -> bool:
        delete_sql = self._query("DELETE FROM revocation_cache WHERE expires_at <= ?")
        select_sql = self._query("SELECT 1 FROM revocation_cache WHERE token_id = ?")
        with self._lock:
            with self._connect() as connection:
                connection.execute(delete_sql, (now,))
                row = connection.execute(select_sql, (token_id,)).fetchone()
                connection.commit()
        return row is not None


_shared_state_backend: SharedStateBackend | None = None


def get_shared_state_backend() -> SharedStateBackend:
    """Return the default shared state backend."""

    global _shared_state_backend
    if _shared_state_backend is None:
        _shared_state_backend = SharedStateBackend()
    return _shared_state_backend


def reset_shared_state_backend() -> None:
    """Reset the shared state backend singleton for tests or config reloads."""

    global _shared_state_backend
    _shared_state_backend = None