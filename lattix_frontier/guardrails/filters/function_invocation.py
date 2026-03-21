"""Function/tool invocation validation filter."""

from __future__ import annotations

from lattix_frontier.guardrails.filter_chain import Filter, FilterContext, FilterResult


class FunctionInvocationFilter(Filter):
    """Validate tool invocation metadata before and after execution."""

    async def evaluate(self, envelope, context: FilterContext) -> FilterResult:  # type: ignore[override]
        if envelope.action.startswith("read_") and envelope.target_agent == "external":
            return FilterResult(action="block", envelope=envelope, reason="external read blocked")
        return FilterResult(action="pass", envelope=envelope)
