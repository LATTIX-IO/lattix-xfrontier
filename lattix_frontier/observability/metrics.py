"""Lightweight in-process metrics registry."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping


class MetricsRegistry:
    """Minimal metrics collector compatible with unit tests and local runs."""

    def __init__(self) -> None:
        self._counters: Counter[str] = Counter()

    def increment(self, metric: str, value: int = 1) -> None:
        self._counters[metric] += value

    def snapshot(self) -> Mapping[str, int]:
        return dict(self._counters)


metrics = MetricsRegistry()
