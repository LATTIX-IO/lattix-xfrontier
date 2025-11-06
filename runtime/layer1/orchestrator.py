from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Callable, Iterable, Optional

from ..layer2.contracts import Envelope, Budget
from ..layer2.event_bus import EventBus
from ..layer2.registry import AgentsRegistry
from ..layer2.policy import BudgetClock, within_time
from ..layer2.middleware import attach_default_middlewares
from ..network.dispatcher import TopicDispatcher
from pathlib import Path as _Path


class Orchestrator:
    def __init__(self, registry_path: Path) -> None:
        self.bus = EventBus()
        self.registry = AgentsRegistry(registry_path)
        attach_default_middlewares(self.bus, strict=False)

    def run_stage(
        self,
        name: str,
        topic: str,
        payload: Dict[str, Any],
        budget_ms: int = 10_000,
        expected_keys: Optional[Iterable[str]] = None,
        done_when: Optional[Callable[[Envelope], bool]] = None,
        dispatch_mode: str = "local",
        remote_map_path: Optional["_Path"] = None,
    ) -> Envelope:
        clock = BudgetClock()
        env = Envelope(
            msg_type=f"stage:{name}",
            sender="orchestrator",
            topic=topic,
            budget=Budget(time_limit_ms=budget_ms),
            payload=payload,
        )
        # Deliver locally or dispatch to remote services
        if dispatch_mode == "remote":
            dispatcher = TopicDispatcher(_Path(remote_map_path or "runtime/network/topic_endpoints.example.json").resolve())
            # Best-effort remote dispatch; response recorded in payload
            resp = dispatcher.dispatch(topic, env)
            try:
                (env.payload.setdefault("remote_responses", []).append(resp))  # type: ignore
            except Exception:
                pass
        else:
            self.bus.publish(topic, env)
        # Check termination conditions
        def is_done() -> bool:
            if done_when is not None:
                try:
                    return bool(done_when(env))
                except Exception:
                    return True  # fail-safe
            if expected_keys:
                return all(k in (env.payload or {}) for k in expected_keys)
            return True

        if not is_done():
            # In a real async system, we would wait for events. Here, we respect time budget and return.
            pass
        return env


def registry_path_default() -> Path:
    return Path("AGENTS/REGISTRY/agents.registry.json").resolve()


def demo_orchestration() -> None:
    orch = Orchestrator(registry_path_default())
    # Example: GTM content stage broadcast
    env = orch.run_stage(
        name="gtm-content",
        topic="gtm.content",
        payload={"brief": "Launch announcement draft"},
        budget_ms=2000,
    )
    print(env.to_json())


if __name__ == "__main__":
    demo_orchestration()
