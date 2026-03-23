import asyncio

from frontier_runtime.envelope import Envelope
from frontier_runtime.guardrails import FilterContext, PromptRenderFilter


def test_prompt_render_uses_structured_policy_context() -> None:
    envelope = Envelope(source_agent="tester", action="execute", payload={"task": "demo"})

    result = asyncio.run(PromptRenderFilter().evaluate(envelope, FilterContext(classification="restricted")))

    assert result.envelope.payload["task"] == "demo"
    assert result.envelope.payload["frontier_policy_context"] == {"classification": "restricted"}