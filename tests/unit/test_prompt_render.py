import asyncio

from lattix_frontier.envelope.models import Envelope
from lattix_frontier.guardrails.filter_chain import FilterContext
from lattix_frontier.guardrails.filters.prompt_render import PromptRenderFilter


def test_prompt_render_uses_structured_policy_context() -> None:
    envelope = Envelope(source_agent="tester", action="execute", payload={"task": "demo"})

    result = asyncio.run(PromptRenderFilter().evaluate(envelope, FilterContext(classification="restricted")))

    assert result.envelope.payload["task"] == "demo"
    assert result.envelope.payload["frontier_policy_context"] == {"classification": "restricted"}