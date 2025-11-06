from __future__ import annotations
import itertools
import json
from pathlib import Path
from typing import Dict, List, Optional

from ..layer2.contracts import Envelope
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
            return None
        url = next(self._iters[topic]) if topic in self._iters else urls[0]
        # Add correlation id header via A2A default; token is injected in a2a.post_envelope
        return post_envelope(url, env, sub=sub)

