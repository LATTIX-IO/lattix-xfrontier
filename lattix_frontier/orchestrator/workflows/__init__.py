"""Predefined workflow catalog."""

from __future__ import annotations

from lattix_frontier.orchestrator.workflows.base import Workflow
from lattix_frontier.orchestrator.workflows.gtm_content import GTMContentWorkflow
from lattix_frontier.orchestrator.workflows.ops_project import OpsProjectWorkflow
from lattix_frontier.orchestrator.workflows.security_compliance import SecurityComplianceWorkflow


def get_workflow_catalog() -> dict[str, Workflow]:
    """Return the built-in workflow catalog."""

    return {
        "gtm_content": GTMContentWorkflow(),
        "security_compliance": SecurityComplianceWorkflow(),
        "ops_project": OpsProjectWorkflow(),
    }
