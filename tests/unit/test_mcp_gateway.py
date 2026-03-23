import asyncio

from frontier_runtime.mcp import MCPGateway, ToolRegistry
from frontier_runtime.sandbox import ExecutionSpec


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
