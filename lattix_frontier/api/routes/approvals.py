"""Approval polling and decision routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lattix_frontier.orchestrator.approvals import get_approval_store

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalDecisionRequest(BaseModel):
    decision: str


@router.get("/{approval_id}")
async def get_approval(approval_id: str) -> dict[str, object]:
    request = get_approval_store().get(approval_id)
    if request is None:
        raise HTTPException(status_code=404, detail="approval request not found")
    return request.model_dump(mode="json")


@router.post("/{approval_id}/decision")
async def decide_approval(approval_id: str, request: ApprovalDecisionRequest) -> dict[str, object]:
    if request.decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'rejected'")
    store = get_approval_store()
    existing = store.get(approval_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="approval request not found")
    updated = store.decide(approval_id, request.decision)
    return updated.model_dump(mode="json")