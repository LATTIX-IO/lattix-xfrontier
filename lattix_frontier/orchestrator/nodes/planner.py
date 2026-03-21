"""Task planning node."""

from __future__ import annotations

from lattix_frontier.orchestrator.state import OrchestratorState


async def planner_node(state: OrchestratorState) -> OrchestratorState:
    """Decompose a task into simple execution steps."""

    plan = [segment.strip() for segment in state.task.split(" and ") if segment.strip()]
    if not plan:
        plan = [state.task]
    return state.model_copy(update={"plan": plan})
