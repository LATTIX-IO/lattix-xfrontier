"""Focused tests for mention-driven multi-agent collaboration."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if not str(os.environ.get("A2A_JWT_SECRET") or "").strip():
    os.environ["A2A_JWT_SECRET"] = "unit-test-super-secret-value-32bytes"
if not str(os.environ.get("FRONTIER_API_BEARER_TOKEN") or "").strip():
    os.environ["FRONTIER_API_BEARER_TOKEN"] = "unit-test-bearer"

import app.main as main_module
from app.main import store


@dataclass
class _FakeAgent:
    id: str
    name: str
    config_json: dict[str, Any] = field(default_factory=dict)


def test_extract_agent_mentions_dedup_and_order() -> None:
    mentions = main_module._extract_agent_mentions("hey @analyst and @researcher, also @analyst again")
    assert mentions == ["analyst", "researcher"]


def test_resolve_collaboration_turns_precedence() -> None:
    agent = _FakeAgent(id="a", name="A", config_json={"max_collaboration_turns": 9})
    # payload overrides agent config
    assert main_module._resolve_collaboration_turns(agent, {"max_collaboration_turns": 3}) == 3
    # agent config when no payload
    assert main_module._resolve_collaboration_turns(agent, {}) == 9
    # default when neither
    assert main_module._resolve_collaboration_turns(_FakeAgent("b", "B"), {}) == 6
    # capped
    assert main_module._resolve_collaboration_turns(agent, {"max_collaboration_turns": 999}) == 20


def _wire_fakes(monkeypatch, *, gate_respond: bool = True) -> None:
    agents = {
        "analyst": _FakeAgent("a-analyst", "Analyst"),
        "researcher": _FakeAgent("a-researcher", "Researcher"),
    }
    monkeypatch.setattr(
        main_module, "_resolve_published_agent_definition", lambda token: agents.get(str(token).lower())
    )
    monkeypatch.setattr(main_module, "_resolve_agent_system_prompt", lambda a, requested_token=None: ("sys", "src"))
    monkeypatch.setattr(main_module, "_resolve_agent_chat_model", lambda a: "gpt-test")
    monkeypatch.setattr(main_module, "_augment_system_prompt_with_skills", lambda p: p)

    def fake_chat(*, system_prompt: str, user_prompt: str, model: str = "", **_kwargs):
        if "routing gate" in system_prompt:
            payload = '{"respond": true, "reason": "asked"}' if gate_respond else '{"respond": false, "reason": "n/a"}'
            return payload, {"mode": "live"}
        return "Acknowledged. Nothing further.", {"mode": "live"}

    monkeypatch.setattr(main_module, "_run_openai_chat", fake_chat)


def test_collaboration_threads_responses_under_parent(monkeypatch) -> None:
    _wire_fakes(monkeypatch, gate_respond=True)
    run_id = "collab-thread-test"
    store.run_events[run_id] = []
    try:
        turns = main_module._run_agent_collaboration(
            run_id=run_id,
            root_event_id="root-evt",
            initial_agent_id="a-primary",
            initial_agent_name="Primary",
            seed_text="@analyst please help",
            transcript_seed="Primary: opening",
            max_turns=6,
            mask_secrets=False,
        )
        assert turns >= 1
        analyst_events = [
            e for e in store.run_events[run_id] if e.metadata and e.metadata.get("selected_agent_name") == "Analyst"
        ]
        assert analyst_events, "analyst should have been invoked"
        evt = analyst_events[0]
        assert evt.metadata["parent_event_id"] == "root-evt"
        assert evt.metadata["thread_id"] == "root-evt"
        assert evt.metadata["decision"]["respond"] is True
    finally:
        store.run_events.pop(run_id, None)


def test_collaboration_records_decline(monkeypatch) -> None:
    _wire_fakes(monkeypatch, gate_respond=False)
    run_id = "collab-decline-test"
    store.run_events[run_id] = []
    try:
        main_module._run_agent_collaboration(
            run_id=run_id,
            root_event_id="root-evt",
            initial_agent_id="a-primary",
            initial_agent_name="Primary",
            seed_text="@analyst thoughts?",
            transcript_seed="Primary: opening",
            max_turns=6,
            mask_secrets=False,
        )
        declined = [e for e in store.run_events[run_id] if e.metadata and e.metadata.get("declined")]
        assert declined, "a declined gate should still record an event"
        assert declined[0].metadata["decision"]["respond"] is False
    finally:
        store.run_events.pop(run_id, None)


def test_collaboration_respects_turn_cap(monkeypatch) -> None:
    _wire_fakes(monkeypatch, gate_respond=True)
    run_id = "collab-cap-test"
    store.run_events[run_id] = []
    try:
        turns = main_module._run_agent_collaboration(
            run_id=run_id,
            root_event_id="root-evt",
            initial_agent_id="a-primary",
            initial_agent_name="Primary",
            seed_text="@analyst @researcher both please",
            transcript_seed="Primary: opening",
            max_turns=1,
            mask_secrets=False,
        )
        assert turns == 1
    finally:
        store.run_events.pop(run_id, None)
