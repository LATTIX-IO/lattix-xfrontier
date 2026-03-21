"""Root orchestration graph and execution helpers."""

from __future__ import annotations

from typing import Any
import uuid

from lattix_frontier.config import get_settings
from lattix_frontier.events.nats_client import get_event_bus
from lattix_frontier.guardrails.filter_chain import FilterContext
from lattix_frontier.orchestrator.checkpointer import build_checkpointer
from lattix_frontier.orchestrator.nodes.critic import critic_node
from lattix_frontier.orchestrator.nodes.executor import executor_node
from lattix_frontier.orchestrator.nodes.human_gate import human_gate_node
from lattix_frontier.orchestrator.nodes.planner import planner_node
from lattix_frontier.orchestrator.nodes.router import router_node
from lattix_frontier.orchestrator.state import OrchestratorState

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # pragma: no cover
    END = "END"
    START = "START"
    StateGraph = None  # type: ignore[assignment]


async def _emit_node_event(node_name: str, state: OrchestratorState) -> None:
    bus = get_event_bus()
    await bus.publish_node_event(node_name=node_name, state=state)


async def _apply_node(node_name: str, state: OrchestratorState, func: Any) -> OrchestratorState:
    if not state.budget.has_remaining_capacity():
        return state.model_copy(update={"errors": [*state.errors, f"budget exceeded before {node_name}"]})
    await _emit_node_event(node_name, state)
    return await func(state)


def build_graph() -> Any:
    """Build a LangGraph StateGraph when available.

    TODO(owner=platform, reason=add true LangGraph interrupt/resume persistence semantics).
    """

    settings = get_settings()
    checkpointer = build_checkpointer(settings)
    if checkpointer is not None and not hasattr(checkpointer, "get_next_version"):
        checkpointer = None
    if StateGraph is None:
        return {"checkpointer": checkpointer, "fallback": True}
    graph = StateGraph(OrchestratorState)
    graph.add_node("planner", planner_node)
    graph.add_node("router", router_node)
    graph.add_node("executor", executor_node)
    graph.add_node("critic", critic_node)
    graph.add_node("human_gate", human_gate_node)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "router")
    graph.add_edge("router", "executor")
    graph.add_edge("executor", "critic")
    graph.add_conditional_edges(
        "critic",
        lambda state: "router" if state.errors and state.retry_count < 2 else "human_gate" if state.requires_approval else END,
        {"router": "router", "human_gate": "human_gate", END: END},
    )
    graph.add_conditional_edges("human_gate", lambda state: END, {END: END})
    return graph.compile(checkpointer=checkpointer)


async def run_graph(initial_state: OrchestratorState) -> OrchestratorState:
    """Run the orchestration graph, using a deterministic fallback when LangGraph is unavailable."""

    async def _run_without_langgraph(state: OrchestratorState) -> OrchestratorState:
        state = await _apply_node("planner", state, planner_node)
        state = await _apply_node("router", state, router_node)
        state = await _apply_node("executor", state, executor_node)
        state = await _apply_node("critic", state, critic_node)
        if state.errors and state.retry_count < 2:
            state = state.model_copy(update={"retry_count": state.retry_count + 1})
            state = await _apply_node("router", state, router_node)
            state = await _apply_node("executor", state, executor_node)
            state = await _apply_node("critic", state, critic_node)
        if state.requires_approval:
            state = await _apply_node("human_gate", state, human_gate_node)
        return state

    # TODO(owner=platform, reason=restore direct LangGraph runtime invocation once durable checkpoint/resume semantics are stabilized across local and CI environments).
    _ = build_graph()
    _thread_id = initial_state.approval_request_id or f"workflow-{uuid.uuid5(uuid.NAMESPACE_URL, initial_state.task)}"
    return await _run_without_langgraph(initial_state)
