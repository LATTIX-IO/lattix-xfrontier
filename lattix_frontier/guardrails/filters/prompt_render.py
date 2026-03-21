"""Prompt rendering and prompt injection of policy context."""

from __future__ import annotations

from lattix_frontier.guardrails.filter_chain import Filter, FilterContext, FilterResult


class PromptRenderFilter(Filter):
    """Inject system guidance into outbound prompts."""

    async def evaluate(self, envelope, context: FilterContext) -> FilterResult:  # type: ignore[override]
        payload = dict(envelope.payload)
        policy_context = dict(payload.get("frontier_policy_context", {}))
        policy_context["classification"] = context.classification
        payload["frontier_policy_context"] = policy_context
        return FilterResult(action="modify", envelope=envelope.model_copy(update={"payload": payload}))
