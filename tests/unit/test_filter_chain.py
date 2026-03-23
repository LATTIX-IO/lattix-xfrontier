import asyncio

from frontier_runtime.envelope import Envelope
from frontier_runtime.guardrails import FilterContext, default_filter_chain
from frontier_runtime.security import CapabilityMinter, build_default_keypair


def test_filter_chain_allows_valid_envelope() -> None:
    token = CapabilityMinter(build_default_keypair()).mint_agent_token(
        agent_id="research",
        allowed_tools=["execute_step"],
        allowed_read_paths=[],
        allowed_write_paths=[],
        max_tool_calls=1,
    )
    envelope = Envelope(
        source_agent="backend",
        target_agent="research",
        action="execute_step",
        payload={"task": "research foo"},
        capability_token=token.decode("utf-8"),
    )
    result = asyncio.run(default_filter_chain().run(envelope, FilterContext()))
    assert result.action in {"pass", "modify"}


def test_filter_chain_blocks_targeted_envelope_without_capability_token() -> None:
    envelope = Envelope(source_agent="backend", target_agent="research", action="execute_step", payload={"task": "research foo"})

    result = asyncio.run(default_filter_chain().run(envelope, FilterContext()))

    assert result.action == "block"
    assert result.reason == "capability token required"
