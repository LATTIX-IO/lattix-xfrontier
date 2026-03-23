from __future__ import annotations
import itertools
import json
from pathlib import Path
from typing import Dict, List, Optional

from ..layer2.contracts import Envelope
from ..layer2.reporting import add_trace, increment_metric
from ..layer2.security import enforce_runtime_envelope_security
from .a2a import post_envelope


class TopicDispatcher:
    def __init__(self, mapping_path: Path) -> None:
        self._path = mapping_path
        self._map: Dict[str, List[str]] = {}
        self._iters: Dict[str, itertools.cycle] = {}
        self.reload()

    def reload(self) -> None:
        self._map = json.loads(self._path.read_text(encoding="utf-8"))
        self._iters = {k: itertools.cycle(v) for k, v in self._map.items() if v}

    def dispatch(self, topic: str, env: Envelope, sub: str = "orchestrator") -> Optional[Dict]:
        urls = self._map.get(topic) or []
        if not urls:
            add_trace(env, "network.dispatch", "skipped", {"reason": "no_registered_url", "topic": topic})
            return None
        url = next(self._iters[topic]) if topic in self._iters else urls[0]
        auth = enforce_runtime_envelope_security(env)
        increment_metric(env, "remote_dispatch_attempts", 1)
        add_trace(env, "network.dispatch", "attempt", {"topic": topic, "url": url, "subject": auth.subject or sub})
        # Add correlation id header via A2A default; token is injected in a2a.post_envelope
        try:
            response = post_envelope(
                url,
                env,
                sub=auth.subject or sub,
                actor=auth.actor,
                tenant_id=auth.tenant_id or None,
                internal_service=auth.internal_service,
            )
        except Exception as exc:
            increment_metric(env, "remote_dispatch_failures", 1)
            add_trace(env, "network.dispatch", "error", {"topic": topic, "url": url, "reason": str(exc)})
            raise
        increment_metric(env, "remote_dispatch_successes", 1)
        add_trace(env, "network.dispatch", "delivered", {"topic": topic, "url": url})
        return response

