from __future__ import annotations
from typing import Any, Dict
from .contracts import Envelope


def ensure_metrics(env: Envelope) -> Dict[str, Any]:
    if not isinstance(env.payload, dict):
        env.payload = {}
    metrics = env.payload.get("metrics")
    if not isinstance(metrics, dict):
        metrics = {}
        env.payload["metrics"] = metrics
    metrics.setdefault("tokens_used", 0)
    return metrics


def add_tokens(env: Envelope, tokens: int) -> None:
    m = ensure_metrics(env)
    try:
        m["tokens_used"] = int(m.get("tokens_used", 0)) + int(tokens)
    except Exception:
        m["tokens_used"] = int(tokens)


def add_log(env: Envelope, key: str, value: Any) -> None:
    if not isinstance(env.payload, dict):
        env.payload = {}
    logs = env.payload.get("logs")
    if not isinstance(logs, list):
        logs = []
        env.payload["logs"] = logs
    logs.append({key: value})

