"""Event stream route handlers."""

from __future__ import annotations

from fastapi import APIRouter

from lattix_frontier.events.nats_client import get_event_bus

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
async def list_events() -> list[dict[str, object]]:
    bus = get_event_bus()
    return [event.model_dump(mode="json") for event in bus.events]
