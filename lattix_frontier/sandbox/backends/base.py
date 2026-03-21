"""Base sandbox backend abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from lattix_frontier.sandbox.artifacts import WorkspaceLayout
from lattix_frontier.sandbox.executor import ExecutionResult, ExecutionSpec, SandboxPlan
from lattix_frontier.sandbox.policy import SandboxPolicy


class SandboxBackend(ABC):
    """Backend abstraction for planning and running sandboxed tools."""

    def __init__(self, policy: SandboxPolicy) -> None:
        self.policy = policy

    @abstractmethod
    def plan(self, spec: ExecutionSpec, workspace: WorkspaceLayout) -> SandboxPlan:
        """Build a backend-specific execution plan."""

    @abstractmethod
    async def execute(self, spec: ExecutionSpec, workspace: WorkspaceLayout, plan: SandboxPlan) -> ExecutionResult:
        """Execute the planned command and return the result."""
