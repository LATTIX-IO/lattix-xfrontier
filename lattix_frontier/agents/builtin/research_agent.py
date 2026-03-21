"""Research agent implementation."""

from __future__ import annotations

from lattix_frontier.agents.base import LattixAgent, Tool
from lattix_frontier.envelope.models import Envelope, EnvelopeStatus


class ResearchAgent(LattixAgent):
    agent_id = "research"
    name = "Research Agent"
    description = "Performs lightweight research and document analysis."
    skills = ["research", "analysis"]
    tools = [Tool(id="search", description="Search trusted sources")]
    system_prompt = "Gather facts, highlight evidence, and stay concise."
    port = 8081

    async def handle(self, envelope: Envelope) -> Envelope:
        task = str(envelope.payload.get("task", ""))
        return envelope.model_copy(
            update={
                "status": EnvelopeStatus.COMPLETED,
                "payload": {"result": f"research complete for: {task}"},
            }
        )
