"""Structured logging configuration."""

from __future__ import annotations

import logging
from typing import Any

try:
    import structlog
except ImportError:  # pragma: no cover - fallback for minimal environments.
    structlog = None  # type: ignore[assignment]


_REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = {"authorization", "token", "access_token", "refresh_token", "secret", "password", "api_key", "key"}


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in _SENSITIVE_KEYS:
                sanitized[key] = _REDACTED
            else:
                sanitized[key] = _sanitize(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize(item) for item in value)
    return value


def _sanitize_event(_, __, event_dict: dict[str, Any]) -> dict[str, Any]:
    return {key: _sanitize(value) for key, value in event_dict.items()}


def configure_logging(level: str = "INFO") -> None:
    """Configure standard logging and structlog when available."""

    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
    if structlog is not None:
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.add_log_level,
                _sanitize_event,
                structlog.processors.JSONRenderer(),
            ]
        )


def get_logger(name: str) -> Any:
    """Return a structured logger when available, otherwise a standard logger."""

    if structlog is not None:
        return structlog.get_logger(name)
    return logging.getLogger(name)
