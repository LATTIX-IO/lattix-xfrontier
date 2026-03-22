from __future__ import annotations
import os
from typing import Any, Dict

try:
    from fastapi import FastAPI, Request, HTTPException
except Exception:  # pragma: no cover
    FastAPI = None  # type: ignore
    Request = Any  # type: ignore
    HTTPException = Exception  # type: ignore

from runtime.layer2.contracts import Envelope
from runtime.layer2.validation import validate_envelope_dict
from runtime.security.jwt import verify_token, JWTConfig


app = FastAPI(title=os.getenv("SERVICE_NAME", "agent-service")) if FastAPI else None


def _authz(request: Request) -> None:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = auth.split(" ", 1)[1]
    verify_token(token, JWTConfig())


if app:
    @app.get("/healthz")
    def healthz() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> Dict[str, str]:
        return {"status": "ready"}

    @app.post("/v1/envelope")
    async def handle_envelope(req: Request) -> Dict[str, Any]:
        _authz(req)
        data = await req.json()
        # Basic validation
        errs = validate_envelope_dict(data)
        if errs:
            raise HTTPException(status_code=400, detail={"errors": errs})
        env = Envelope.from_json(__import__("json").dumps(data))
        # Correlation consistency (if header provided)
        corr_hdr = req.headers.get("X-Correlation-ID") or req.headers.get("x-correlation-id")
        if corr_hdr and corr_hdr != env.correlation_id:
            raise HTTPException(status_code=400, detail={"errors": ["correlation_id mismatch"]})
        # TODO: call agent runtime handler or enqueue work
        corr = data.get("correlation_id")
        return {"accepted": True, "envelope_id": env.id, "correlation_id": corr}
