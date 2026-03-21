import asyncio

from lattix_frontier.mcp.gateway import MCPGateway
from lattix_frontier.mcp.tool_registry import ToolRegistry
from lattix_frontier.sandbox.executor import ExecutionSpec


def test_mcp_gateway_plans_tool_execution() -> None:
    registry = ToolRegistry()
    registry.register("python", "Python interpreter")
    gateway = MCPGateway(registry=registry)
    result = asyncio.run(
        gateway.plan_tool_execution(
            agent_id="orchestrator",
            spec=ExecutionSpec(tool_id="python", command=["python", "-c", "print('hi')"]),
        )
    )
    assert result.plan.backend in {"docker-linux", "docker-macos", "docker-windows"}
