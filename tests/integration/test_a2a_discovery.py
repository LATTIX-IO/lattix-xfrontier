import asyncio

from frontier_runtime.agents import discover_agents


def test_discovery_finds_builtin_agents() -> None:
    agents = asyncio.run(discover_agents())
    assert len(agents) >= 3
