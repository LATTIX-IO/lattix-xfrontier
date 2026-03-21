import asyncio

from lattix_frontier.events.event_models import AgentEvent
from lattix_frontier.events.nats_client import get_event_bus
from lattix_frontier.security.event_signing import verify_event_signature


def test_event_bus_signs_events() -> None:
    bus = get_event_bus()
    event = asyncio.run(bus.publish(AgentEvent(event_type="demo", source="tester")))
    assert event.signature is not None
    assert event.signer == "tester"
    assert verify_event_signature(event) is True