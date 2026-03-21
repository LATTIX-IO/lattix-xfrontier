"""In-memory rate limiter for MCP tools."""

from __future__ import annotations

import time


class RateLimiter:
    """Per-agent per-tool fixed window rate limiter."""

    def __init__(self, limit: int = 10, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[tuple[str, str], list[float]] = {}

    def allow(self, agent_id: str, tool_id: str) -> bool:
        now = time.time()
        key = (agent_id, tool_id)
        values = [stamp for stamp in self._events.get(key, []) if now - stamp < self.window_seconds]
        if len(values) >= self.limit:
            self._events[key] = values
            return False
        values.append(now)
        self._events[key] = values
        return True
