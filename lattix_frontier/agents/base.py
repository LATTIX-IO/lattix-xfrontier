"""Base classes for Frontier agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from lattix_frontier.envelope.models import Envelope


class Tool(BaseModel):
    """Minimal MCP tool metadata model."""

    id: str
    description: str


class LattixAgent(ABC):
    """Abstract Frontier agent interface."""

    agent_id: str
    name: str
    description: str
    skills: list[str]
    tools: list[Tool]
    system_prompt: str
    port: int = 8080

    @abstractmethod
    async def handle(self, envelope: Envelope) -> Envelope:
        """Process an envelope and return the result envelope."""

    def agent_card(self) -> dict[str, Any]:
        """Return an A2A-style agent card."""

        return {
            "name": self.name,
            "description": self.description,
            "url": f"http://localhost:{self.port}",
            "version": "1.0.0",
            "capabilities": {"streaming": False, "pushNotifications": False},
            "defaultInputModes": ["application/json"],
            "defaultOutputModes": ["application/json"],
            "skills": [{"id": skill, "name": skill} for skill in self.skills],
        }
