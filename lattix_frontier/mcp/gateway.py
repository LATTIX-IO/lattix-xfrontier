"""MCP gateway facade."""

from __future__ import annotations

from lattix_frontier.mcp.rate_limiter import RateLimiter
from lattix_frontier.mcp.tool_registry import ToolRegistry
from lattix_frontier.sandbox.executor import ExecutionResult, ExecutionSpec
from lattix_frontier.sandbox.manager import ToolJailService
from lattix_frontier.sandbox.policy import SandboxPolicy


class MCPGateway:
    """Route MCP requests with authorization and rate limiting."""

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        limiter: RateLimiter | None = None,
        tool_jail: ToolJailService | None = None,
    ) -> None:
        self.registry = registry or ToolRegistry()
        self.limiter = limiter or RateLimiter()
        self.tool_jail = tool_jail or ToolJailService()

    def route(self, agent_id: str, tool_id: str) -> bool:
        return tool_id in self.registry.list_tools() and self.limiter.allow(agent_id, tool_id)

    async def plan_tool_execution(
        self,
        agent_id: str,
        spec: ExecutionSpec,
        policy: SandboxPolicy | None = None,
    ) -> ExecutionResult:
        """Authorize and plan sandboxed execution for a registered tool."""

        if not self.route(agent_id, spec.tool_id):
            msg = f"Tool {spec.tool_id} is not authorized for agent {agent_id}"
            raise PermissionError(msg)
        return await self.tool_jail.plan(spec, policy=policy)
