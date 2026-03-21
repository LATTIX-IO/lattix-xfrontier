"""Workflow base class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from lattix_frontier.orchestrator.graph import run_graph
from lattix_frontier.orchestrator.state import OrchestratorState


class Workflow(ABC):
    """Abstract workflow definition."""

    name: str
    classification: str = "internal"

    @abstractmethod
    def seed_task(self, task: str) -> str:
        """Normalize user input into a workflow-specific task."""

    async def run(
        self,
        task: str,
        *,
        approval_request_id: str | None = None,
        approved: bool = False,
    ) -> OrchestratorState:
        """Run the workflow through the orchestration graph."""

        state = OrchestratorState(
            task=self.seed_task(task),
            classification=self.classification,
            approval_request_id=approval_request_id,
            approved=approved,
        )
        return await run_graph(state)
