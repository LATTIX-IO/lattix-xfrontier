"""HTTP client for Agent-to-Agent calls."""

from __future__ import annotations

import httpx

from lattix_frontier.agents.registry import build_default_registry
from lattix_frontier.envelope.models import Envelope, EnvelopeStatus
from lattix_frontier.security.jwt_auth import mint_token, verify_token


class A2AClient:
    """Dispatch envelopes to local or remote agents."""

    async def dispatch(self, envelope: Envelope) -> Envelope:
        registry = build_default_registry()
        if envelope.target_agent is None:
            return envelope.model_copy(update={"status": EnvelopeStatus.FAILED, "errors": ["missing target_agent"]})
        if envelope.target_agent in {record.agent_id for record in registry.list_agents()}:
            agent = registry.get(envelope.target_agent)
            return await agent.handle(envelope)
        port = 8080
        async with httpx.AsyncClient(timeout=15.0) as client:
            bearer = mint_token(
                "orchestrator",
                ttl_seconds=30,
                nonce=envelope.correlation_id,
                additional_claims={"token_use": "a2a_request", "target_agent": envelope.target_agent},
            )
            response = await client.post(
                f"http://localhost:{port}/v1/envelope",
                json=envelope.model_dump(mode="json"),
                headers={"Authorization": f"Bearer {bearer}", "X-Correlation-ID": envelope.correlation_id},
            )
            response.raise_for_status()
            assertion = response.headers.get("X-Agent-Assertion")
            if not assertion:
                return envelope.model_copy(update={"status": EnvelopeStatus.FAILED, "errors": ["missing agent assertion"]})
            claims = verify_token(assertion, nonce=envelope.correlation_id)
            if claims.get("sub") != envelope.target_agent:
                return envelope.model_copy(update={"status": EnvelopeStatus.FAILED, "errors": ["unexpected agent assertion subject"]})
            return Envelope.model_validate(response.json())
