"""Code agent implementation."""

from __future__ import annotations

from lattix_frontier.agents.base import LattixAgent, Tool
from lattix_frontier.envelope.models import Envelope, EnvelopeStatus


class CodeAgent(LattixAgent):
    agent_id = "code"
    name = "Code Agent"
    description = "Builds implementation drafts and technical artifacts."
    skills = ["code", "implementation"]
    tools = [Tool(id="generate_code", description="Generate code artifacts")]
    system_prompt = "Implement clearly, safely, and with tests in mind."
    port = 8082

    async def handle(self, envelope: Envelope) -> Envelope:
        task = str(envelope.payload.get("task", ""))
        return envelope.model_copy(
            update={"status": EnvelopeStatus.COMPLETED, "payload": {"result": f"code draft ready for: {task}"}}
        )
