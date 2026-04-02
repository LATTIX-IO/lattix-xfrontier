from __future__ import annotations

import asyncio
import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from frontier_runtime.persistence import load_state, mutate_state
from frontier_runtime.security import sign_event


@dataclass
class AgentEvent:
    event_type: str
    source: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    previous_hash: str | None = None
    event_hash: str | None = None
    signature: str | None = None
    signer: str | None = None


class HashChain:
    def __init__(self) -> None:
        self._previous_hash: str | None = None

    def append(self, event: AgentEvent) -> AgentEvent:
        event.previous_hash = self._previous_hash
        event.signer = event.signer or event.source
        event.event_hash = _hash_event(event)
        self._previous_hash = event.event_hash
        return event

    def verify(self, events: list[AgentEvent]) -> tuple[bool, int | None]:
        previous_hash: str | None = None
        for index, event in enumerate(events):
            if event.previous_hash != previous_hash:
                return False, index
            if event.event_hash != _hash_event(event):
                return False, index
            previous_hash = event.event_hash
        return True, None


class FallbackEventStore:
    def list_events(self) -> list[AgentEvent]:
        state = load_state()
        return [AgentEvent(**payload) for payload in state.get("events", [])]


class EventBus:
    def __init__(self) -> None:
        self.fallback = FallbackEventStore()

    async def publish(self, event: AgentEvent) -> AgentEvent:
        await asyncio.sleep(0)
        existing = self.fallback.list_events()
        event.previous_hash = existing[-1].event_hash if existing else None
        event.signer = event.signer or event.source
        event.event_hash = _hash_event(event)
        event.signature = sign_event(event)

        def _mutate(snapshot: dict[str, Any]) -> None:
            events = list(snapshot.get("events", []))
            events.append(asdict(event))
            snapshot["events"] = events[-5000:]

        mutate_state(_mutate)
        return event


def _hash_event(event: AgentEvent) -> str:
    hasher = hashlib.sha256()
    hasher.update(str(event.previous_hash or "").encode("utf-8"))
    hasher.update(str(event.event_type).encode("utf-8"))
    hasher.update(str(event.source).encode("utf-8"))
    hasher.update(str(event.signer or event.source).encode("utf-8"))
    hasher.update(str(event.payload).encode("utf-8"))
    hasher.update(str(event.created_at).encode("utf-8"))
    return hasher.hexdigest()


_EVENT_BUS: EventBus | None = None


def get_event_bus() -> EventBus:
    global _EVENT_BUS
    if _EVENT_BUS is None:
        _EVENT_BUS = EventBus()
    return _EVENT_BUS


def reset_event_bus() -> None:
    global _EVENT_BUS
    _EVENT_BUS = None
