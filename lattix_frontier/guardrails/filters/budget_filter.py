"""Budget enforcement filter."""

from __future__ import annotations

from lattix_frontier.guardrails.filter_chain import Filter, FilterContext, FilterResult


class BudgetFilter(Filter):
    """Block envelopes that exceed token, time, or cost limits."""

    async def evaluate(self, envelope, context: FilterContext) -> FilterResult:  # type: ignore[override]
        if not envelope.budget.has_remaining_capacity():
            return FilterResult(action="block", envelope=envelope, reason="budget exceeded")
        return FilterResult(action="pass", envelope=envelope)
