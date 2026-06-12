"""Focused tests for mention-driven multi-agent collaboration."""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if not str(os.environ.get("A2A_JWT_SECRET") or "").strip():
    os.environ["A2A_JWT_SECRET"] = "unit-test-super-secret-value-32bytes"
if not str(os.environ.get("FRONTIER_API_BEARER_TOKEN") or "").strip():
    os.environ["FRONTIER_API_BEARER_TOKEN"] = "unit-test-bearer"

import app.main as main_module
from app.main import app, store

client = TestClient(app)
ADMIN_HEADERS = {"Authorization": "Bearer unit-test-bearer", "x-frontier-actor": "frontier-admin"}


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
        # The full, untruncated answer must be carried for the chat view.
        assert evt.metadata.get("full_text"), "collaboration messages must carry full_text"
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


def test_endpoint_run_triggers_multi_agent_collaboration(monkeypatch) -> None:
    """End-to-end: POST /workflow-runs with a multi-agent prompt drives the
    executor → collaboration loop, producing a threaded second-agent reply.

    The provider is stubbed to behave 'live': the primary agent @-mentions the
    operations agent, the decide-to-respond gate says yes, and the operations
    agent replies (then stops). Exercises the real endpoint and run executor.
    """
    published = {main_module._slugify(a.name) for a in store.agent_definitions.values() if a.status == "published"}
    assert {"demo-research-agent", "demo-operations-agent"} <= published, "seeded demo agents required"

    def fake_chat(*_args: Any, **kwargs: Any):
        system = str(kwargs.get("system_prompt") or "")
        user = str(kwargs.get("user_prompt") or "")
        if "routing gate" in system:
            return '{"respond": true, "reason": "directly asked"}', {"mode": "live", "model": "test"}
        if "collaborating in a multi-agent run" in user:
            return "Action item created. Nothing further.", {"mode": "live", "model": "test"}
        # primary agent response — hand off to the operations agent
        return (
            "Research complete. @demo-operations-agent please turn this into an action item.",
            {"mode": "live", "model": "test"},
        )

    monkeypatch.setattr(main_module, "_run_openai_chat", fake_chat)

    created = client.post(
        "/workflow-runs",
        json={
            "prompt": "@demo-research-agent research the topic, then @demo-operations-agent act on it.",
            "tokens": [
                {"kind": "agent", "value": "demo-research-agent"},
                {"kind": "agent", "value": "demo-operations-agent"},
            ],
        },
        headers=ADMIN_HEADERS,
    )
    assert created.status_code == 200
    run_id = created.json()["id"]
    try:
        # The run executes on a background worker; poll its events.
        ops_event = None
        for _ in range(80):
            events = store.run_events.get(run_id, [])
            ops_event = next(
                (
                    e
                    for e in events
                    if e.type == "agent_message"
                    and (e.metadata or {}).get("selected_agent_name") == "Demo Operations Agent"
                    and (e.metadata or {}).get("parent_event_id")
                ),
                None,
            )
            if ops_event is not None:
                break
            time.sleep(0.1)

        assert ops_event is not None, "operations agent should have been @-called and threaded a reply"
        assert ops_event.metadata["thread_id"], "reply should carry a thread id"
        assert ops_event.metadata["decision"]["respond"] is True
    finally:
        store.runs.pop(run_id, None)
        store.run_events.pop(run_id, None)
        store.run_details.pop(run_id, None)


def test_send_run_message_continues_same_run(monkeypatch) -> None:
    """POST /workflow-runs/{id}/messages appends to THIS run's conversation and
    responds in place — no new run is spawned."""

    def fake_chat(*_args: Any, **kwargs: Any):
        system = str(kwargs.get("system_prompt") or "")
        if "routing gate" in system:
            return '{"respond": false, "reason": "n/a"}', {"mode": "live", "model": "test"}
        return "Here is my in-run reply.", {"mode": "live", "model": "test"}

    monkeypatch.setattr(main_module, "_run_openai_chat", fake_chat)

    created = client.post(
        "/workflow-runs",
        json={"prompt": "Start a simple chat task."},
        headers=ADMIN_HEADERS,
    )
    assert created.status_code == 200
    run_id = created.json()["id"]
    try:
        # Wait for the initial execution to land its agent message.
        for _ in range(80):
            if any(e.type == "agent_message" for e in store.run_events.get(run_id, [])):
                break
            time.sleep(0.1)
        before_agent_msgs = sum(
            1 for e in store.run_events.get(run_id, []) if e.type == "agent_message"
        )
        run_count_before = len(store.runs)

        sent = client.post(
            f"/workflow-runs/{run_id}/messages",
            json={"message": "Thanks — now summarize that in one line."},
            headers=ADMIN_HEADERS,
        )
        assert sent.status_code == 200
        assert sent.json()["run_id"] == run_id

        # The user's message lands in this run immediately.
        assert any(
            e.type == "user_message" and "summarize" in e.summary
            for e in store.run_events[run_id]
        )

        # The agent reply lands in this same run (background worker).
        reply = None
        for _ in range(80):
            agent_msgs = [e for e in store.run_events[run_id] if e.type == "agent_message"]
            if len(agent_msgs) > before_agent_msgs:
                reply = agent_msgs[-1]
                break
            time.sleep(0.1)
        assert reply is not None, "in-run reply should be appended to the same run"
        assert reply.metadata.get("full_text"), "in-run replies must carry full_text"
        assert len(store.runs) == run_count_before, "no new run should be created"

        for _ in range(50):
            if store.runs[run_id].status == "Done":
                break
            time.sleep(0.1)
        assert store.runs[run_id].status == "Done"
    finally:
        store.runs.pop(run_id, None)
        store.run_events.pop(run_id, None)
        store.run_details.pop(run_id, None)


def test_send_run_message_requires_text() -> None:
    runs = client.get("/workflow-runs", headers={"x-frontier-actor": "frontier-admin"}).json()
    if not runs:
        return
    response = client.post(
        f"/workflow-runs/{runs[0]['id']}/messages", json={}, headers=ADMIN_HEADERS
    )
    assert response.status_code == 400


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
