"""JWT authentication middleware for admin APIs."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from lattix_frontier.security.jwt_auth import verify_token


class AuthMiddleware(BaseHTTPMiddleware):
    """Verify JWTs for protected admin routes."""

    _public_paths = {"/", "/health", "/ready", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in self._public_paths:
            request.state.auth_context = {"authenticated": False, "subject": "anonymous"}
            return await call_next(request)
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth or not auth.lower().startswith("bearer "):
            return JSONResponse(status_code=401, content={"detail": "missing bearer token"})
        token = auth.split(" ", 1)[1]
        try:
            claims = verify_token(token, require_nonce=False, enforce_replay=False)
        except ValueError as exc:
            return JSONResponse(status_code=401, content={"detail": str(exc)})
        request.state.auth_context = {"authenticated": True, "subject": claims.get("sub"), "claims": claims}
        return await call_next(request)
