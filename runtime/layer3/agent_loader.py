from __future__ import annotations
import importlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from ..layer2.contracts import Envelope
from ..layer2.event_bus import EventBus
from ..layer2.registry import AgentsRegistry
from ..layer2.reporting import add_log


def _try_import(module_path: str, function_name: str) -> Optional[Callable[[Envelope], None]]:
    try:
        mod = importlib.import_module(module_path)
        fn = getattr(mod, function_name)
        if callable(fn):
            return fn
    except Exception:
        return None
    return None


def _load_runtime_cfg(agent_dir: Path) -> Optional[Dict[str, Any]]:
    cfg_path = agent_dir / "agent.runtime.json"
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _default_handler(agent_id: str, agent_name: str) -> Callable[[Envelope], None]:
    def _h(env: Envelope) -> None:
        add_log(env, "l3", f"{agent_id} observed {env.topic}")
        participants = env.payload.setdefault("participants", []) if isinstance(env.payload, dict) else None
        if isinstance(participants, list):
            participants.append({"agent": agent_id, "name": agent_name})
    return _h


def register_agents(
    bus: EventBus,
    registry: AgentsRegistry,
    agents_root: Path,
    include_ids: Optional[Iterable[str]] = None,
) -> int:
    """Register Layer 3 agents on the bus.

    Priority per agent:
    1) agent.runtime.json topics + (module,function) -> import and subscribe
    2) agent.runtime.json topics only -> subscribe default handler
    3) no runtime.json -> skip (use tag-based auto-registration if desired)
    """
    filter_ids = set(include_ids or [])
    count = 0
    for agent in registry.all():
        agent_id = agent["id"]
        if filter_ids and agent_id not in filter_ids:
            continue
        agent_name = agent.get("name", agent_id)
        agent_dir = agents_root / agent_id
        runtime_cfg = _load_runtime_cfg(agent_dir)
        if not runtime_cfg:
            continue
        topics: List[str] = list(runtime_cfg.get("topics", []))
        mod = runtime_cfg.get("module")
        fn = runtime_cfg.get("function", "handle")
        handler: Optional[Callable[[Envelope], None]] = None
        if mod:
            handler = _try_import(mod, fn)
        if handler is None:
            handler = _default_handler(agent_id, agent_name)
        for t in topics:
            bus.subscribe(t, handler)
            count += 1
    return count

