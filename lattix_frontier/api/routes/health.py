"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from lattix_frontier.config import get_settings
from lattix_frontier.federation.service import FederationTopologyService

router = APIRouter(tags=["health"])


@router.get("/")
async def root() -> dict[str, object]:
    """Return a small discovery payload for anonymous local/browser access."""

    settings = get_settings()
    return {
        "service": settings.app_name,
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "message": "Interactive UI is available via the frontend or local gateway. API routes require a bearer token.",
    }


@router.get("/health")
async def health() -> dict[str, object]:
    """Return a simple liveness response."""

    settings = get_settings()
    federation_status = FederationTopologyService(settings).status()
    return {
        "status": "ok",
        "service": settings.app_name,
        "federation": {
            "enabled": federation_status.enabled,
            "cluster_name": federation_status.cluster_name,
            "region": federation_status.region,
            "peer_count": len(federation_status.peers),
        },
    }


@router.get("/ready")
async def ready() -> dict[str, str]:
    """Return a simple readiness response."""

    return {"status": "ready"}
