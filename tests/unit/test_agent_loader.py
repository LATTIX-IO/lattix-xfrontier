from __future__ import annotations

import json
from pathlib import Path

from apps.workers.runtime.layer2.contracts import Envelope
from apps.workers.runtime.layer2.event_bus import EventBus
from apps.workers.runtime.layer2.registry import AgentsRegistry
from apps.workers.runtime.layer3.agent_loader import register_agents


def _write_registry(path: Path, agents: list[dict[str, object]]) -> AgentsRegistry:
    path.write_text(json.dumps({"agents": agents}), encoding="utf-8")
    return AgentsRegistry(path)


def test_register_agents_skips_invalid_explicit_module_handler(tmp_path: Path) -> None:
    registry = _write_registry(
        tmp_path / "registry.json",
        [
            {
                "id": "planner",
                "name": "Planner",
            }
        ],
    )
    agents_root = tmp_path / "agents"
    agent_dir = agents_root / "planner"
    agent_dir.mkdir(parents=True)
    (agent_dir / "agent.runtime.json").write_text(
        json.dumps(
            {
                "topics": ["gtm.content"],
                "module": "nonexistent.module",
                "function": "handle",
            }
        ),
        encoding="utf-8",
    )

    bus = EventBus()
    count = register_agents(bus=bus, registry=registry, agents_root=agents_root)

    assert count == 0
    env = Envelope(topic="gtm.content", sender="backend")
    bus.publish("gtm.content", env)
    assert env.payload.get("participants") is None
    assert env.payload.get("logs") is None


def test_register_agents_preserves_topics_only_default_handler(tmp_path: Path) -> None:
    registry = _write_registry(
        tmp_path / "registry.json",
        [
            {
                "id": "planner",
                "name": "Planner",
            }
        ],
    )
    agents_root = tmp_path / "agents"
    agent_dir = agents_root / "planner"
    agent_dir.mkdir(parents=True)
    (agent_dir / "agent.runtime.json").write_text(
        json.dumps(
            {
                "topics": ["gtm.content"],
            }
        ),
        encoding="utf-8",
    )

    bus = EventBus()
    count = register_agents(bus=bus, registry=registry, agents_root=agents_root)

    assert count == 1
    env = Envelope(topic="gtm.content", sender="backend")
    bus.publish("gtm.content", env)
    assert env.payload["participants"] == [{"agent": "planner", "name": "Planner"}]
    assert any(
        item.get("l3") == "planner observed gtm.content"
        for item in env.payload.get("logs", [])
        if isinstance(item, dict)
    )


def test_register_agents_loads_allowlisted_agent_local_module(tmp_path: Path) -> None:
    registry = _write_registry(
        tmp_path / "registry.json",
        [
            {
                "id": "planner",
                "name": "Planner",
            }
        ],
    )
    agents_root = tmp_path / "agents"
    agent_dir = agents_root / "planner"
    agent_dir.mkdir(parents=True)
    (agent_dir / "__init__.py").write_text("", encoding="utf-8")
    (agent_dir / "handler.py").write_text(
        "from apps.workers.runtime.layer2.contracts import Envelope\n\n"
        "def handle(env: Envelope) -> None:\n"
        "    env.payload['loaded_by'] = 'planner.handler'\n",
        encoding="utf-8",
    )
    (agent_dir / "agent.runtime.json").write_text(
        json.dumps(
            {
                "topics": ["gtm.content"],
                "module": "planner.handler",
                "function": "handle",
            }
        ),
        encoding="utf-8",
    )

    bus = EventBus()
    count = register_agents(bus=bus, registry=registry, agents_root=agents_root)

    assert count == 1
    env = Envelope(topic="gtm.content", sender="backend")
    bus.publish("gtm.content", env)
    assert env.payload["loaded_by"] == "planner.handler"


def test_register_agents_rejects_disallowed_module_namespace(tmp_path: Path) -> None:
    registry = _write_registry(
        tmp_path / "registry.json",
        [
            {
                "id": "planner",
                "name": "Planner",
            }
        ],
    )
    agents_root = tmp_path / "agents"
    agent_dir = agents_root / "planner"
    agent_dir.mkdir(parents=True)
    (agent_dir / "agent.runtime.json").write_text(
        json.dumps(
            {
                "topics": ["gtm.content"],
                "module": "os",
                "function": "system",
            }
        ),
        encoding="utf-8",
    )

    bus = EventBus()
    count = register_agents(bus=bus, registry=registry, agents_root=agents_root)

    assert count == 0
