"""Agent routing node."""

from __future__ import annotations

from lattix_frontier.orchestrator.state import OrchestratorState


async def router_node(state: OrchestratorState) -> OrchestratorState:
    """Select a target agent for the current step."""

    if not state.plan:
        return state.model_copy(update={"errors": [*state.errors, "no plan available"]})
    current_task = state.plan[min(state.current_step, len(state.plan) - 1)].lower()
    if any(token in current_task for token in ("research", "analyze", "discover")):
        target = "research"
    elif any(token in current_task for token in ("code", "build", "implement")):
        target = "code"
    else:
        target = "review"
    outputs = dict(state.agent_outputs)
    outputs["target_agent"] = target
    return state.model_copy(update={"agent_outputs": outputs})
