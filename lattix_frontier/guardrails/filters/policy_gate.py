"""OPA policy evaluation filter."""

from __future__ import annotations

from lattix_frontier.guardrails.filter_chain import Filter, FilterContext, FilterResult
from lattix_frontier.security.opa_client import OPAClient


class PolicyGateFilter(Filter):
    """Consult policy engine before allowing execution."""

    def __init__(self) -> None:
        self.client = OPAClient()

    async def evaluate(self, envelope, context: FilterContext) -> FilterResult:  # type: ignore[override]
        decision = await self.client.evaluate(
            policy="agent_policy",
            payload={
                "agent_id": envelope.source_agent,
                "tool": envelope.action,
                "resource": envelope.target_agent or "workflow",
                "budget": envelope.budget.model_dump(),
                "classification": context.classification,
                "action": envelope.action,
                "provider": envelope.metadata.get("provider", "local"),
            },
        )
        if not decision.allowed:
            return FilterResult(action="block", envelope=envelope, reason=decision.reason)
        return FilterResult(action="pass", envelope=envelope)
