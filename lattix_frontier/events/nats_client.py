"""NATS JetStream client abstraction."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

try:
    import nats
except ImportError:  # pragma: no cover - optional in constrained environments.
    nats = None  # type: ignore[assignment]

from lattix_frontier.config import get_settings
from lattix_frontier.events.event_models import AgentEvent
from lattix_frontier.events.hash_chain import HashChain
from lattix_frontier.orchestrator.state import OrchestratorState
from lattix_frontier.persistence.state_backend import get_shared_state_backend
from lattix_frontier.security.event_signing import sign_event


@dataclass
class InMemoryEventBus:
    """SQLite-backed fallback event bus used in tests and local dry runs."""

    chain: HashChain = field(init=False)

    def __post_init__(self) -> None:
        self._backend = get_shared_state_backend()
        last_hash = self._backend.get_last_event_hash()
        self.chain = HashChain(genesis_hash="genesis")
        self.chain._last_hash = last_hash

    async def publish(self, event: AgentEvent) -> AgentEvent:
        chained = self.chain.append(event)
        chained = sign_event(chained)
        self._backend.put_event(
            chained.id,
            chained.created_at.isoformat(),
            chained.model_dump_json(),
            chained.event_hash,
        )
        return chained

    async def publish_node_event(self, node_name: str, state: OrchestratorState) -> AgentEvent:
        return await self.publish(
            AgentEvent(event_type="orchestrator.node", source=node_name, payload={"task": state.task})
        )

    def list_events(self) -> list[AgentEvent]:
        return [AgentEvent.model_validate_json(item) for item in self._backend.list_events()]


@dataclass
class NATSEventBus:
    """JetStream-backed event bus with in-memory fallback for local/test runs."""

    fallback: InMemoryEventBus = field(default_factory=InMemoryEventBus)
    _connection: object | None = None
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _disabled: bool = False

    async def _get_connection(self):
        if self._disabled:
            return None
        if nats is None:
            return None
        if self._connection is not None and getattr(self._connection, "is_connected", False):
            return self._connection
        async with self._lock:
            if self._connection is not None and getattr(self._connection, "is_connected", False):
                return self._connection
            settings = get_settings()
            try:
                self._connection = await nats.connect(settings.nats_url, connect_timeout=1, max_reconnect_attempts=1)
            except Exception:
                self._connection = None
                self._disabled = True
            return self._connection

    async def publish(self, event: AgentEvent) -> AgentEvent:
        chained = await self.fallback.publish(event)
        connection = await self._get_connection()
        if connection is None:
            return chained
        settings = get_settings()
        try:
            jetstream = connection.jetstream()
            await jetstream.add_stream(name=settings.nats_stream, subjects=[settings.nats_subject])
        except Exception:
            pass
        try:
            await connection.jetstream().publish(settings.nats_subject, chained.model_dump_json().encode("utf-8"))
        except Exception:
            return chained
        return chained

    async def publish_node_event(self, node_name: str, state: OrchestratorState) -> AgentEvent:
        return await self.publish(AgentEvent(event_type="orchestrator.node", source=node_name, payload={"task": state.task}))


_event_bus: NATSEventBus | None = None


def get_event_bus() -> NATSEventBus:
    """Return the default event bus implementation."""

    global _event_bus
    if _event_bus is None:
        _event_bus = NATSEventBus()
    return _event_bus


def reset_event_bus() -> None:
    """Reset the default event bus singleton for tests or config reloads."""

    global _event_bus
    _event_bus = None
