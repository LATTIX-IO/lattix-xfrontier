from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .contracts import Envelope
from .event_bus import EventBus
from .registry import AgentsRegistry
from .reporting import add_log


def _load_topic_map(path: Path) -> Dict[str, List[str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def auto_register_by_tags(
    bus: EventBus,
    registry: AgentsRegistry,
    topic_map_path: Path,
    include_tags: Optional[Iterable[str]] = None,
) -> int:
    """Registers placeholder subscribers for agents based on tags -> topics map.

    This scaffolds the L3 interface. Replace subscribers with real agent handlers later.
    Returns the count of registrations.
    """
    tag_filter = set(t.lower() for t in include_tags) if include_tags else None
    topic_map = _load_topic_map(topic_map_path)
    count = 0

    def make_handler(agent_id: str, agent_name: str) -> callable:
        def _handler(env: Envelope) -> None:
            # Placeholder: record participation only
            participants = env.payload.setdefault("participants", []) if isinstance(env.payload, dict) else None
            if isinstance(participants, list):
                participants.append({"agent": agent_id, "name": agent_name})
            add_log(env, "auto", f"{agent_id} observed {env.topic}")
        return _handler

    for agent in registry.all():
        agent_id = agent["id"]
        agent_name = agent.get("name", agent_id)
        tags = [t.lower() for t in (agent.get("tags") or [])]
        if tag_filter and not any(t in tag_filter for t in tags):
            continue
        topics: List[str] = []
        for t in tags:
            topics.extend(topic_map.get(t, []))
        for topic in sorted(set(topics)):
            bus.subscribe(topic, make_handler(agent_id, agent_name))
            count += 1
    return count

