"""Policy route handlers."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("")
async def list_policies() -> list[str]:
    return sorted(path.name for path in Path("policies").glob("*.rego"))
