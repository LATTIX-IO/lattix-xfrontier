from __future__ import annotations

import time
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
    metrics.setdefault("security_allowed", 0)
    metrics.setdefault("security_blocked", 0)
    metrics.setdefault("security_errors", 0)
    metrics.setdefault("event_bus_delivery_attempts", 0)
    metrics.setdefault("event_bus_delivery_successes", 0)
    metrics.setdefault("event_bus_delivery_blocked", 0)
    metrics.setdefault("event_bus_delivery_failures", 0)
    metrics.setdefault("remote_dispatch_attempts", 0)
    metrics.setdefault("remote_dispatch_successes", 0)
    metrics.setdefault("remote_dispatch_failures", 0)
    return metrics


def increment_metric(env: Envelope, key: str, amount: int = 1) -> int:
    metrics = ensure_metrics(env)
    try:
        metrics[key] = int(metrics.get(key, 0)) + int(amount)
    except Exception:
        metrics[key] = int(amount)
    return int(metrics[key])


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


def add_trace(
    env: Envelope, stage: str, outcome: str, metadata: dict[str, Any] | None = None
) -> None:
    event = {
        "ts_ms": int(time.time() * 1000),
        "correlation_id": env.correlation_id,
        "stage": str(stage or "runtime.unknown").strip() or "runtime.unknown",
        "outcome": str(outcome or "unknown").strip() or "unknown",
    }
    if isinstance(metadata, dict) and metadata:
        event["metadata"] = metadata
    add_log(env, "trace", event)


def _ensure_security_events(env: Envelope) -> list[dict[str, Any]]:
    if not isinstance(env.payload, dict):
        env.payload = {}
    events = env.payload.get("security_events")
    if not isinstance(events, list):
        events = []
        env.payload["security_events"] = events
    return events


def add_security_event(
    env: Envelope,
    outcome: str,
    control: str,
    *,
    reason: str = "",
    auth_context: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    event: dict[str, Any] = {
        "ts_ms": int(time.time() * 1000),
        "correlation_id": env.correlation_id,
        "topic": env.topic,
        "outcome": str(outcome or "unknown").strip() or "unknown",
        "control": str(control or "runtime.security").strip() or "runtime.security",
    }
    if reason:
        event["reason"] = str(reason)
    if isinstance(auth_context, dict):
        sanitized_auth = {
            "actor": str(auth_context.get("actor") or "").strip(),
            "tenant_id": str(auth_context.get("tenant_id") or "").strip(),
            "subject": str(auth_context.get("subject") or "").strip(),
            "internal_service": bool(auth_context.get("internal_service")),
            "session_id": str(auth_context.get("session_id") or "").strip(),
        }
        event["auth_context"] = {
            key: value for key, value in sanitized_auth.items() if value not in {"", None}
        }
    if isinstance(metadata, dict) and metadata:
        event["metadata"] = metadata

    _ensure_security_events(env).append(event)

    normalized_outcome = event["outcome"].lower()
    metric_key = "security_errors"
    if normalized_outcome == "allowed":
        metric_key = "security_allowed"
    elif normalized_outcome == "blocked":
        metric_key = "security_blocked"
    increment_metric(env, metric_key, 1)
    add_trace(
        env,
        "runtime.security",
        normalized_outcome,
        {
            "control": event["control"],
            "reason": event.get("reason", ""),
            "topic": env.topic,
        },
    )
