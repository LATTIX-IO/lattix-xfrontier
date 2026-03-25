from __future__ import annotations
"""
Template for a choreographed subscriber handling a specific topic.
Copy this into your runtime package and register it with the EventBus.
"""
from runtime.layer2.contracts import Envelope


TOPIC = "example.topic"


def handle(env: Envelope) -> None:
    if env.topic != TOPIC:
        return
    # Validate and enrich payload
    env.payload.setdefault("artifacts", []).append({"by": "example", "note": "processed"})

