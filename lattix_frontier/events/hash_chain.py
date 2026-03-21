"""Tamper-evident hash chain implementation."""

from __future__ import annotations

import hashlib
import json

from lattix_frontier.events.event_models import AgentEvent


class HashChain:
    """Cryptographic hash chain for append-only event integrity."""

    def __init__(self, genesis_hash: str = "genesis") -> None:
        self.genesis_hash = genesis_hash
        self._last_hash = genesis_hash

    def append(self, event: AgentEvent) -> AgentEvent:
        """Compute hash and link the event to the previous entry."""

        event_data = event.model_dump(exclude={"event_hash", "prev_hash"}, mode="json")
        canonical_json = json.dumps(event_data, sort_keys=True, separators=(",", ":"))
        event_hash = hashlib.sha256(f"{self._last_hash}|{canonical_json}".encode("utf-8")).hexdigest()
        chained = event.model_copy(update={"prev_hash": self._last_hash, "event_hash": event_hash})
        self._last_hash = event_hash
        return chained

    def verify(self, events: list[AgentEvent]) -> tuple[bool, int | None]:
        """Verify the integrity of a chain of events."""

        previous = self.genesis_hash
        for index, event in enumerate(events):
            event_data = event.model_dump(exclude={"event_hash", "prev_hash"}, mode="json")
            canonical_json = json.dumps(event_data, sort_keys=True, separators=(",", ":"))
            expected = hashlib.sha256(f"{previous}|{canonical_json}".encode("utf-8")).hexdigest()
            if event.prev_hash != previous or event.event_hash != expected:
                return False, index
            previous = event.event_hash
        return True, None
