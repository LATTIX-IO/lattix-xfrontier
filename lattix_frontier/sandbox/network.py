"""Egress mediation helpers for sandbox policies."""

from __future__ import annotations

from fnmatch import fnmatch
from urllib.parse import urlparse

from pydantic import BaseModel, Field


class EgressPolicy(BaseModel):
    """Resolved egress configuration for a sandbox execution."""

    allowed_hosts: list[str] = Field(default_factory=list)
    proxy_url: str | None = None
    network_name: str = "none"


def normalize_host(target: str) -> str:
    """Normalize a host or URL into a hostname-like token."""

    parsed = urlparse(target if "://" in target else f"https://{target}")
    return (parsed.hostname or target).strip().lower()


def is_host_allowed(target: str, allowlist: list[str]) -> bool:
    """Return whether the host matches an allowlist entry."""

    if not allowlist:
        return False
    host = normalize_host(target)
    return any(fnmatch(host, pattern.lower()) for pattern in allowlist)
