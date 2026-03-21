"""Capability token validation filter."""

from __future__ import annotations

from lattix_frontier.guardrails.filter_chain import Filter, FilterContext, FilterResult
from lattix_frontier.security.biscuit_tokens import CapabilityVerifier, build_default_keypair


class CapabilityFilter(Filter):
    """Validate capability tokens when present."""

    def __init__(self) -> None:
        self.verifier = CapabilityVerifier(build_default_keypair())

    async def evaluate(self, envelope, context: FilterContext) -> FilterResult:  # type: ignore[override]
        if envelope.capability_token is None:
            if envelope.target_agent is not None:
                return FilterResult(action="block", envelope=envelope, reason="capability token required")
            return FilterResult(action="pass", envelope=envelope)
        allowed = self.verifier.verify(
            token=envelope.capability_token.encode("utf-8"),
            requested_action=envelope.action,
            resource=envelope.target_agent or "unknown",
        )
        if not allowed:
            return FilterResult(action="block", envelope=envelope, reason="invalid capability token")
        return FilterResult(action="pass", envelope=envelope)
