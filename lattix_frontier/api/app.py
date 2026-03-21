"""FastAPI application factory for the Frontier control plane."""

from __future__ import annotations

from fastapi import FastAPI

from lattix_frontier.api.middleware.auth import AuthMiddleware
from lattix_frontier.api.middleware.security_headers import SecurityHeadersMiddleware
from lattix_frontier.api.middleware.telemetry import TelemetryMiddleware
from lattix_frontier.api.routes import agents, approvals, events, federation, health, policies, workflows
from lattix_frontier.config import get_settings
from lattix_frontier.observability.logging import configure_logging
from lattix_frontier.observability.tracing import configure_tracing


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    configure_logging(settings.log_level)
    configure_tracing(settings.app_name, settings.jaeger_endpoint)

    app = FastAPI(title="Lattix Frontier", version="0.1.0")
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(TelemetryMiddleware)
    app.add_middleware(AuthMiddleware)
    app.include_router(health.router)
    app.include_router(agents.router)
    app.include_router(workflows.router)
    app.include_router(approvals.router)
    app.include_router(events.router)
    app.include_router(policies.router)
    app.include_router(federation.router)
    return app
