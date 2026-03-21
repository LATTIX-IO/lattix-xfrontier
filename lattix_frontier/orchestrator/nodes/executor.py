"""Agent dispatch node."""

from __future__ import annotations

from lattix_frontier.agents.a2a_client import A2AClient
from lattix_frontier.envelope.models import Envelope, EnvelopeStatus
from lattix_frontier.guardrails.filter_chain import FilterChain, FilterContext, default_filter_chain
from lattix_frontier.orchestrator.state import OrchestratorState
from lattix_frontier.security.biscuit_tokens import CapabilityMinter, build_default_keypair


async def executor_node(state: OrchestratorState) -> OrchestratorState:
    """Create an execution envelope, run guardrails, and dispatch to an agent."""

    target_agent = str(state.agent_outputs.get("target_agent", "review"))
    step_task = state.plan[min(state.current_step, len(state.plan) - 1)] if state.plan else state.task
    minter = CapabilityMinter(build_default_keypair())
    token = minter.mint_agent_token(
        agent_id=target_agent,
        allowed_tools=["execute_step"],
        allowed_read_paths=[],
        allowed_write_paths=[],
        max_tool_calls=1,
    )
    envelope = Envelope(
        source_agent="orchestrator",
        target_agent=target_agent,
        workflow_id="default",
        action="execute_step",
        payload={"task": step_task},
        budget=state.budget,
        capability_token=token.decode("utf-8"),
        status=EnvelopeStatus.IN_PROGRESS,
    )
    chain: FilterChain = default_filter_chain()
    result = await chain.run(envelope, FilterContext(classification=state.classification))
    if result.action == "block":
        return state.model_copy(update={"errors": [*state.errors, result.reason or "blocked"]})
    client = A2AClient()
    response_envelope = await client.dispatch(result.envelope)
    outputs = dict(state.agent_outputs)
    outputs[target_agent] = response_envelope.payload
    return state.model_copy(update={"envelopes": [*state.envelopes, response_envelope], "agent_outputs": outputs})
