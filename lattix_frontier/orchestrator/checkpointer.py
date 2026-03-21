"""Checkpointing abstraction for LangGraph execution."""

from __future__ import annotations

from typing import Any

from lattix_frontier.config import Settings

try:
    from langgraph.checkpoint.postgres import PostgresSaver
except ImportError:  # pragma: no cover
    PostgresSaver = None  # type: ignore[assignment]


def build_checkpointer(settings: Settings) -> Any:
    """Create a Postgres-based checkpointer when the dependency is available."""

    if PostgresSaver is None:
        return None
        if not settings.database_url.startswith(("postgresql://", "postgres://")):
            return None
    return PostgresSaver.from_conn_string(settings.database_url)
