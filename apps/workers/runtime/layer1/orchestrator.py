from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Callable, Iterable, Optional

from ..layer2.contracts import Envelope, Budget
from ..layer2.event_bus import EventBus
from ..layer2.registry import AgentsRegistry
from ..layer2.reporting import add_trace
from ..layer2.security import resolve_runtime_auth_context
from ..layer2.policy import BudgetClock, within_time
from ..layer2.middleware import attach_default_middlewares
from ..network.dispatcher import TopicDispatcher
from pathlib import Path as _Path
from ..paths import default_registry_path, topic_endpoints_map_path


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
        actor: str | None = None,
        tenant_id: str | None = None,
        session_id: str | None = None,
        internal_service: bool = True,
    ) -> Envelope:
        clock = BudgetClock()
        next_payload = dict(payload or {})
        auth_context = next_payload.get("auth_context") if isinstance(next_payload.get("auth_context"), dict) else {}
        if actor:
            auth_context.setdefault("actor", actor)
        if tenant_id:
            auth_context.setdefault("tenant_id", tenant_id)
        if session_id:
            auth_context.setdefault("session_id", session_id)
        auth_context.setdefault("subject", "orchestrator")
        auth_context.setdefault("internal_service", internal_service)
        next_payload["auth_context"] = auth_context
        env = Envelope(
            msg_type=f"stage:{name}",
            sender="orchestrator",
            topic=topic,
            budget=Budget(time_limit_ms=budget_ms),
            payload=next_payload,
        )
        resolve_runtime_auth_context(env)
        # Deliver locally or dispatch to remote services
        if dispatch_mode == "remote":
            dispatcher = TopicDispatcher(_Path(remote_map_path or topic_endpoints_map_path()).resolve())
            # Best-effort remote dispatch; response recorded in payload
            try:
                resp = dispatcher.dispatch(topic, env)
            except Exception as exc:
                env.errors.append(f"remote dispatch failed: {exc}")
                add_trace(env, "orchestrator.dispatch", "error", {"topic": topic, "reason": str(exc)})
            else:
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
                except Exception as exc:
                    env.errors.append(f"stage completion check failed: {exc}")
                    add_trace(env, "orchestrator.done_when", "error", {"topic": topic, "reason": str(exc)})
                    return False
            if expected_keys:
                return all(k in (env.payload or {}) for k in expected_keys)
            return True

        if not is_done():
            if not within_time(env.budget, clock):
                env.errors.append("stage time budget exceeded before completion")
                add_trace(env, "orchestrator.stage", "blocked", {"reason": "time_budget_exceeded", "topic": topic})
            # In a real async system, we would wait for events. Here, we respect time budget and return.
            pass
        return env


def registry_path_default() -> Path:
    return default_registry_path()


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
