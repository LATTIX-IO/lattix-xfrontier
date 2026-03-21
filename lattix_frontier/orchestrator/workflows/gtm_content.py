"""GTM content workflow."""

from __future__ import annotations

from lattix_frontier.orchestrator.workflows.base import Workflow


class GTMContentWorkflow(Workflow):
    """Simple workflow for GTM content generation."""

    name = "gtm_content"

    def seed_task(self, task: str) -> str:
        return f"research market and build campaign content and review results for: {task}"
