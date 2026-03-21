"""Ordered guardrail pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field

from lattix_frontier.envelope.models import Envelope


class FilterContext(BaseModel):
    """Execution context passed to filters."""

    classification: str = "internal"
    metadata: dict[str, str] = Field(default_factory=dict)


class FilterResult(BaseModel):
    """Result returned by a filter."""

    action: Literal["pass", "modify", "block"]
    envelope: Envelope
    reason: str | None = None


class Filter(ABC):
    """Abstract base class for filters."""

    @abstractmethod
    async def evaluate(self, envelope: Envelope, context: FilterContext) -> FilterResult:
        """Evaluate an envelope against this filter."""


class FilterChain:
    """Execute filters in order and stop on block."""

    def __init__(self, filters: list[Filter]) -> None:
        self.filters = filters

    async def run(self, envelope: Envelope, context: FilterContext) -> FilterResult:
        current = envelope
        for active_filter in self.filters:
            result = await active_filter.evaluate(current, context)
            if result.action == "block":
                return result
            current = result.envelope
        return FilterResult(action="pass", envelope=current)


def default_filter_chain() -> FilterChain:
    """Build the default ordered filter chain."""

    from lattix_frontier.guardrails.filters.budget_filter import BudgetFilter
    from lattix_frontier.guardrails.filters.capability_filter import CapabilityFilter
    from lattix_frontier.guardrails.filters.dlp_filter import DLPFilter
    from lattix_frontier.guardrails.filters.function_invocation import FunctionInvocationFilter
    from lattix_frontier.guardrails.filters.policy_gate import PolicyGateFilter
    from lattix_frontier.guardrails.filters.prompt_render import PromptRenderFilter

    return FilterChain(
        [
            BudgetFilter(),
            CapabilityFilter(),
            PolicyGateFilter(),
            DLPFilter(),
            PromptRenderFilter(),
            FunctionInvocationFilter(),
        ]
    )
