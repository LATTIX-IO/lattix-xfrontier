"""MCP tool registry."""

from __future__ import annotations


class ToolRegistry:
    """Track available MCP tools."""

    def __init__(self) -> None:
        self._tools: dict[str, str] = {}

    def register(self, tool_id: str, description: str) -> None:
        self._tools[tool_id] = description

    def list_tools(self) -> dict[str, str]:
        return dict(self._tools)
