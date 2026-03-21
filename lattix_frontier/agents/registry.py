"""Agent registry and metadata."""

from __future__ import annotations

from dataclasses import dataclass

from lattix_frontier.agents.base import LattixAgent
from lattix_frontier.agents.builtin.code_agent import CodeAgent
from lattix_frontier.agents.builtin.coordinator_agent import CoordinatorAgent
from lattix_frontier.agents.builtin.research_agent import ResearchAgent
from lattix_frontier.agents.builtin.review_agent import ReviewAgent


@dataclass
class AgentRecord:
    """Serializable registry record."""

    agent_id: str
    name: str
    description: str
    port: int
    skills: list[str]

    def model_dump(self) -> dict[str, object]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "port": self.port,
            "skills": self.skills,
        }


class AgentRegistry:
    """Registry for built-in and discovered agents."""

    def __init__(self, agents: list[LattixAgent]) -> None:
        self._agents = {agent.agent_id: agent for agent in agents}

    def list_agents(self) -> list[AgentRecord]:
        return [
            AgentRecord(
                agent_id=agent.agent_id,
                name=agent.name,
                description=agent.description,
                port=agent.port,
                skills=agent.skills,
            )
            for agent in self._agents.values()
        ]

    def get(self, agent_id: str) -> LattixAgent:
        return self._agents[agent_id]


def build_default_registry() -> AgentRegistry:
    """Create the default built-in agent registry."""

    return AgentRegistry([ResearchAgent(), CodeAgent(), ReviewAgent(), CoordinatorAgent()])
