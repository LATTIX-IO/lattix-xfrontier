"""Federation status route handlers."""

from __future__ import annotations

from fastapi import APIRouter

from lattix_frontier.federation.service import FederationTopologyService

router = APIRouter(prefix="/federation", tags=["federation"])


@router.get("/status")
async def federation_status() -> dict[str, object]:
    """Return the current federation topology metadata."""

    return FederationTopologyService().status().model_dump(mode="json")
