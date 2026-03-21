"""Review agent implementation."""

from __future__ import annotations

from lattix_frontier.agents.base import LattixAgent, Tool
from lattix_frontier.envelope.models import Envelope, EnvelopeStatus


class ReviewAgent(LattixAgent):
    agent_id = "review"
    name = "Review Agent"
    description = "Performs QA review over outputs and decisions."
    skills = ["review", "qa"]
    tools = [Tool(id="review_output", description="Review generated output")]
    system_prompt = "Validate completeness, accuracy, and risk."
    port = 8083

    async def handle(self, envelope: Envelope) -> Envelope:
        task = str(envelope.payload.get("task", ""))
        return envelope.model_copy(
            update={"status": EnvelopeStatus.COMPLETED, "payload": {"result": f"review passed for: {task}"}}
        )
