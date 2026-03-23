from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


_DEFAULT_STATE: dict[str, Any] = {
    "approvals": [],
    "events": [],
    "replay_tokens": [],
}


def _default_state() -> dict[str, Any]:
    return {
        "approvals": [],
        "events": [],
        "replay_tokens": [],
    }


def state_path() -> Path:
    configured = str(os.getenv("FRONTIER_STATE_STORE", ".frontier/runtime-state.json")).strip()
    return Path(configured)


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        return _default_state()
    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_state()
    if not isinstance(raw_data, dict):
        return _default_state()
    data: dict[str, Any] = dict(raw_data)
    for key, default in _DEFAULT_STATE.items():
        if key not in data:
            data[key] = list(default) if isinstance(default, list) else default
    return data


def save_state(state: dict[str, Any]) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def mutate_state(mutator: Any) -> dict[str, Any]:
    state = load_state()
    mutator(state)
    save_state(state)
    return state


def reset_shared_state_backend() -> None:
    """Reset in-memory handles while preserving persisted state."""
    return None
