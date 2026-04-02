from __future__ import annotations
import collections
import time
from typing import Callable, DefaultDict, List

from .contracts import Envelope
from .reporting import add_trace, increment_metric


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
            if isinstance(msg.payload, dict) and msg.payload.get("_security_blocked"):
                reason = (
                    str(
                        msg.payload.get("_security_block_classification")
                        or msg.payload.get("_security_block_reason")
                        or "security_blocked"
                    ).strip()
                    or "security_blocked"
                )
                increment_metric(msg, "event_bus_delivery_blocked", 1)
                add_trace(msg, "event_bus.delivery", "blocked", {"reason": reason, "topic": topic})
                return
        # Deliver to subscribers with simple budget checks
        subs = list(self._subscribers.get(topic, []))
        for fn in subs:
            increment_metric(msg, "event_bus_delivery_attempts", 1)
            # Time budget enforcement
            if msg.budget and msg.budget.time_limit_ms is not None:
                now_ms = int(time.time() * 1000)
                if now_ms - msg.created_at_ms > msg.budget.time_limit_ms:
                    msg.errors.append("time budget exceeded; stopping delivery")
                    increment_metric(msg, "event_bus_delivery_blocked", 1)
                    add_trace(
                        msg,
                        "event_bus.delivery",
                        "blocked",
                        {
                            "reason": "time_budget_exceeded",
                            "topic": topic,
                            "subscriber": _subscriber_name(fn),
                        },
                    )
                    break
            # Token budget pre-check (if metrics already present)
            metrics = msg.payload.get("metrics") if isinstance(msg.payload, dict) else None
            if metrics and msg.budget and msg.budget.cost_limit_tokens is not None:
                used = metrics.get("tokens_used")
                if isinstance(used, int) and used > msg.budget.cost_limit_tokens:
                    msg.errors.append("token budget exceeded; stopping delivery")
                    increment_metric(msg, "event_bus_delivery_blocked", 1)
                    add_trace(
                        msg,
                        "event_bus.delivery",
                        "blocked",
                        {
                            "reason": "token_budget_exceeded_pre",
                            "topic": topic,
                            "subscriber": _subscriber_name(fn),
                        },
                    )
                    break

            try:
                fn(msg)
            except Exception as e:
                # Non-fatal; record locally
                msg.errors.append(str(e))
                increment_metric(msg, "event_bus_delivery_failures", 1)
                add_trace(
                    msg,
                    "event_bus.delivery",
                    "error",
                    {"reason": str(e), "topic": topic, "subscriber": _subscriber_name(fn)},
                )
            else:
                increment_metric(msg, "event_bus_delivery_successes", 1)
                add_trace(
                    msg,
                    "event_bus.delivery",
                    "delivered",
                    {"topic": topic, "subscriber": _subscriber_name(fn)},
                )
            # Token budget post-check
            metrics = msg.payload.get("metrics") if isinstance(msg.payload, dict) else None
            if metrics and msg.budget and msg.budget.cost_limit_tokens is not None:
                used = metrics.get("tokens_used")
                if isinstance(used, int) and used > msg.budget.cost_limit_tokens:
                    msg.errors.append("token budget exceeded; stopping delivery")
                    increment_metric(msg, "event_bus_delivery_blocked", 1)
                    add_trace(
                        msg,
                        "event_bus.delivery",
                        "blocked",
                        {
                            "reason": "token_budget_exceeded_post",
                            "topic": topic,
                            "subscriber": _subscriber_name(fn),
                        },
                    )
                    break


def _subscriber_name(fn: Subscriber) -> str:
    return getattr(fn, "__name__", "subscriber") or fn.__class__.__name__
