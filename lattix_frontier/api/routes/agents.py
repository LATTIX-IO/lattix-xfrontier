"""Agent route handlers."""

from __future__ import annotations

from fastapi import APIRouter

from lattix_frontier.agents.discovery import discover_agents

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
async def list_agents() -> list[dict[str, object]]:
    return [record.model_dump() for record in await discover_agents()]
