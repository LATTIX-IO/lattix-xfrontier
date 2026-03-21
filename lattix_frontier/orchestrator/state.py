"""State schema for the LangGraph orchestration layer."""

from __future__ import annotations

from operator import add as list_concat
from typing import Annotated, Any

from pydantic import BaseModel, Field

from lattix_frontier.envelope.models import Budget, Envelope


class OrchestratorState(BaseModel):
    """Immutable state flowing through the orchestration graph."""

    task: str
    plan: list[str] = Field(default_factory=list)
    current_step: int = 0
    envelopes: Annotated[list[Envelope], list_concat] = Field(default_factory=list)
    agent_outputs: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    approved: bool = False
    approval_request_id: str | None = None
    approval_status: str | None = None
    budget: Budget = Field(default_factory=Budget)
    classification: str = "internal"
    final_output: str | None = None
    retry_count: int = 0


OrchestratorState.model_rebuild()
