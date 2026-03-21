"""Verify the in-memory event chain."""

from __future__ import annotations

from lattix_frontier.events.hash_chain import HashChain
from lattix_frontier.events.nats_client import get_event_bus


def main() -> None:
    bus = get_event_bus()
    valid, broken_index = HashChain().verify(bus.events)
    print({"valid": valid, "broken_index": broken_index})  # noqa: T201


if __name__ == "__main__":
    main()
