"""Shared SQLite-backed local state helpers."""

from __future__ import annotations

from pathlib import Path

from lattix_frontier.config import get_settings


def resolve_state_store_path() -> Path:
    """Return the configured SQLite-backed state store path."""

    settings = get_settings()
    path = Path(settings.state_store_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path