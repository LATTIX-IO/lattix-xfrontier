"""Request telemetry middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from lattix_frontier.observability.metrics import metrics
from lattix_frontier.observability.tracing import start_span


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Capture simple request metrics and traces."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        with start_span(f"http {request.method} {request.url.path}"):
            metrics.increment("http.requests")
            return await call_next(request)
