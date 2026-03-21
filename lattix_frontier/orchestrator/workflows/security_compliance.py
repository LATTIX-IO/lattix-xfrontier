"""Security compliance workflow."""

from __future__ import annotations

from lattix_frontier.orchestrator.workflows.base import Workflow


class SecurityComplianceWorkflow(Workflow):
    """Workflow for security compliance analysis."""

    name = "security_compliance"
    classification = "confidential"

    def seed_task(self, task: str) -> str:
        return f"research controls and review compliance plan for: {task}"
