from __future__ import annotations
import time
from typing import Optional
from .contracts import Budget


class BudgetClock:
    def __init__(self) -> None:
        self._start = int(time.time() * 1000)

    def elapsed_ms(self) -> int:
        return int(time.time() * 1000) - self._start


def within_time(budget: Budget, clock: BudgetClock) -> bool:
    if budget.time_limit_ms is None:
        return True
    return clock.elapsed_ms() <= budget.time_limit_ms


def within_tokens(budget: Budget, consumed_tokens: Optional[int]) -> bool:
    if budget.cost_limit_tokens is None or consumed_tokens is None:
        return True
    return consumed_tokens <= budget.cost_limit_tokens


def tokens_used_from_payload(payload) -> Optional[int]:
    try:
        metrics = payload.get("metrics", {})
        used = metrics.get("tokens_used")
        return int(used) if used is not None else None
    except Exception:
        return None
