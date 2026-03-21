"""Human approval gate node."""

from __future__ import annotations

from lattix_frontier.orchestrator.approvals import get_approval_store
from lattix_frontier.orchestrator.state import OrchestratorState


async def human_gate_node(state: OrchestratorState) -> OrchestratorState:
    """Interrupt-like approval gate for sensitive operations."""

    if not state.requires_approval:
        return state
    store = get_approval_store()
    if state.approved:
        return state.model_copy(update={"approved": True, "approval_status": "approved"})
    if state.approval_request_id:
        existing = store.get(state.approval_request_id)
        if existing and existing.status == "approved":
            return state.model_copy(update={"approved": True, "approval_status": "approved"})
        if existing and existing.status == "rejected":
            return state.model_copy(update={"approved": False, "approval_status": "rejected", "errors": [*state.errors, "approval rejected"]})
        return state.model_copy(update={"approved": False, "approval_status": "pending"})
    created = store.create(classification=state.classification, task=state.task)
    return state.model_copy(update={"approved": False, "approval_request_id": created.id, "approval_status": "pending"})
