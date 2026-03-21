"""Operational project workflow."""

from __future__ import annotations

from lattix_frontier.orchestrator.workflows.base import Workflow


class OpsProjectWorkflow(Workflow):
    """Workflow for operations planning."""

    name = "ops_project"

    def seed_task(self, task: str) -> str:
        return f"research project requirements and implement execution plan for: {task}"
