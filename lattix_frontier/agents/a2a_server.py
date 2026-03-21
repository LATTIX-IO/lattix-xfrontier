"""FastAPI server for built-in agents."""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from lattix_frontier.agents.registry import build_default_registry
from lattix_frontier.envelope.models import Envelope
from lattix_frontier.security.biscuit_tokens import CapabilityVerifier, build_default_keypair
from lattix_frontier.security.jwt_auth import mint_token, verify_token


def create_agent_app(agent_id: str | None = None) -> FastAPI:
    """Create an A2A server for the selected built-in agent."""

    selected_agent_id = agent_id or os.getenv("AGENT_ID", "research")
    registry = build_default_registry()
    capability_verifier = CapabilityVerifier(build_default_keypair())
    try:
        agent = registry.get(selected_agent_id)
    except KeyError as exc:  # pragma: no cover - startup guard.
        raise RuntimeError(f"Unknown agent: {selected_agent_id}") from exc
    app = FastAPI(title=f"Lattix Agent {selected_agent_id}")

    @app.get("/.well-known/agent-card.json")
    async def agent_card() -> dict[str, object]:
        return agent.agent_card()

    @app.post("/v1/envelope")
    async def execute(request: Request, envelope: Envelope) -> JSONResponse:
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth or not auth.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        token = auth.split(" ", 1)[1]
        try:
            claims = verify_token(token, nonce=envelope.correlation_id)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        if claims.get("sub") != "orchestrator":
            raise HTTPException(status_code=403, detail="unexpected caller subject")
        if envelope.capability_token is None:
            raise HTTPException(status_code=403, detail="capability token required")
        if not capability_verifier.verify(envelope.capability_token.encode("utf-8"), envelope.action, selected_agent_id):
            raise HTTPException(status_code=403, detail="invalid capability token")
        result = await agent.handle(envelope)
        assertion = mint_token(
            selected_agent_id,
            ttl_seconds=30,
            nonce=envelope.correlation_id,
            additional_claims={"token_use": "a2a_response", "envelope_id": result.id},
        )
        return JSONResponse(content=result.model_dump(mode="json"), headers={"X-Agent-Assertion": assertion})

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "agent": selected_agent_id}

    return app


if __name__ == "__main__":
    selected_port = int(os.getenv("AGENT_PORT", "8081"))
    uvicorn.run(create_agent_app(), host="0.0.0.0", port=selected_port)
