"""Workflow route handlers."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from lattix_frontier.orchestrator.workflows import get_workflow_catalog

router = APIRouter(prefix="/workflows", tags=["workflows"])


class WorkflowRunRequest(BaseModel):
    task: str
    approval_request_id: str | None = None
    approved: bool = False


@router.get("")
async def list_workflows() -> list[str]:
    return sorted(get_workflow_catalog().keys())


@router.post("/{workflow_name}/run")
async def run_workflow(workflow_name: str, request: WorkflowRunRequest) -> dict[str, object]:
    workflow = get_workflow_catalog()[workflow_name]
    result = await workflow.run(
        task=request.task,
        approval_request_id=request.approval_request_id,
        approved=request.approved,
    )
    return result.model_dump(mode="json")
