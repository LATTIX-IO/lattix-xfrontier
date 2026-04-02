from __future__ import annotations
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from ..layer2.contracts import Envelope
from ..layer2.event_bus import EventBus
from ..layer2.registry import AgentsRegistry
from ..layer2.reporting import add_log


_SAFE_MODULE_PATH_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")
_WORKERS_ROOT = Path(__file__).resolve().parents[2]


def _module_is_allowed(module_path: str, *, agent_id: str) -> bool:
    if not _SAFE_MODULE_PATH_PATTERN.fullmatch(module_path):
        return False
    return (
        module_path.startswith("runtime.")
        or module_path.startswith("apps.workers.runtime.")
        or module_path == agent_id
        or module_path.startswith(f"{agent_id}.")
    )


def _load_allowed_module(module_path: str, *, agent_id: str, agents_root: Path) -> Any | None:
    if not _module_is_allowed(module_path, agent_id=agent_id):
        return None
    for search_root in (str(_WORKERS_ROOT), str(agents_root)):
        if search_root not in sys.path:
            sys.path.insert(0, search_root)
    existing_module = sys.modules.get(module_path)
    if existing_module is not None:
        return existing_module
    spec = importlib.util.find_spec(module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_path] = module
    spec.loader.exec_module(module)
    return module


def _try_import(
    module_path: str, function_name: str, *, agent_id: str, agents_root: Path
) -> Optional[Callable[[Envelope], None]]:
    try:
        mod = _load_allowed_module(module_path, agent_id=agent_id, agents_root=agents_root)
        if mod is None:
            return None
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
        participants = (
            env.payload.setdefault("participants", []) if isinstance(env.payload, dict) else None
        )
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
            handler = _try_import(mod, fn, agent_id=agent_id, agents_root=agents_root)
            if handler is None:
                continue
        if handler is None:
            handler = _default_handler(agent_id, agent_name)
        for t in topics:
            bus.subscribe(t, handler)
            count += 1
    return count
