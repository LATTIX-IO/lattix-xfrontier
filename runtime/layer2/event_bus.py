from __future__ import annotations
import collections
import time
from typing import Callable, DefaultDict, Dict, List
from .contracts import Envelope


Subscriber = Callable[[Envelope], None]
Middleware = Callable[[Envelope], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, List[Subscriber]] = collections.defaultdict(list)
        self._middlewares: List[Middleware] = []

    def subscribe(self, topic: str, fn: Subscriber) -> None:
        self._subscribers[topic].append(fn)

    def use(self, middleware: Middleware) -> None:
        """Register a middleware called before delivering to subscribers.
        Middleware may mutate the envelope (e.g., validation results, tracing).
        """
        self._middlewares.append(middleware)

    def publish(self, topic: str, msg: Envelope) -> None:
        # Pre-delivery middlewares
        for mw in list(self._middlewares):
            try:
                mw(msg)
            except Exception as e:
                msg.errors.append(str(e))
        # Deliver to subscribers with simple budget checks
        subs = list(self._subscribers.get(topic, []))
        for fn in subs:
            # Time budget enforcement
            if msg.budget and msg.budget.time_limit_ms is not None:
                now_ms = int(time.time() * 1000)
                if now_ms - msg.created_at_ms > msg.budget.time_limit_ms:
                    msg.errors.append("time budget exceeded; stopping delivery")
                    break
            # Token budget pre-check (if metrics already present)
            metrics = msg.payload.get("metrics") if isinstance(msg.payload, dict) else None
            if metrics and msg.budget and msg.budget.cost_limit_tokens is not None:
                used = metrics.get("tokens_used")
                if isinstance(used, int) and used > msg.budget.cost_limit_tokens:
                    msg.errors.append("token budget exceeded; stopping delivery")
                    break

            try:
                fn(msg)
            except Exception as e:
                # Non-fatal; record locally
                msg.errors.append(str(e))
            # Token budget post-check
            metrics = msg.payload.get("metrics") if isinstance(msg.payload, dict) else None
            if metrics and msg.budget and msg.budget.cost_limit_tokens is not None:
                used = metrics.get("tokens_used")
                if isinstance(used, int) and used > msg.budget.cost_limit_tokens:
                    msg.errors.append("token budget exceeded; stopping delivery")
                    break
