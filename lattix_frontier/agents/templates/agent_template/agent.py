"""Template Frontier agent implementation."""

from __future__ import annotations

from lattix_frontier.agents.base import LattixAgent, Tool
from lattix_frontier.envelope.models import Envelope, EnvelopeStatus


class TemplateAgent(LattixAgent):
    agent_id = "template-agent"
    name = "Template Agent"
    description = "Scaffolded Frontier agent."
    skills = ["template"]
    tools = [Tool(id="template_tool", description="Example tool")]
    system_prompt = "Fill in your agent's purpose and policies."
    port = 8090

    async def handle(self, envelope: Envelope) -> Envelope:
        return envelope.model_copy(update={"status": EnvelopeStatus.COMPLETED, "payload": {"result": "template complete"}})
