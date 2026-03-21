"""Agent discovery over registry and optional mDNS."""

from __future__ import annotations

from lattix_frontier.agents.registry import AgentRecord, build_default_registry


async def discover_agents() -> list[AgentRecord]:
    """Discover agents using the local registry.

    TODO(owner=platform, reason=add mDNS/zeroconf broadcasting for multi-host development discovery).
    """

    return build_default_registry().list_agents()
