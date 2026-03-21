"""Output critic node."""

from __future__ import annotations

from lattix_frontier.orchestrator.state import OrchestratorState


async def critic_node(state: OrchestratorState) -> OrchestratorState:
    """Validate the latest agent output and decide whether approval is required."""

    errors = list(state.errors)
    final_output = state.final_output
    if state.envelopes:
        latest = state.envelopes[-1]
        final_output = str(latest.payload.get("result", latest.payload))
        if latest.errors:
            errors.extend(latest.errors)
    requires_approval = state.classification in {"confidential", "restricted"}
    return state.model_copy(update={"errors": errors, "requires_approval": requires_approval, "final_output": final_output})
