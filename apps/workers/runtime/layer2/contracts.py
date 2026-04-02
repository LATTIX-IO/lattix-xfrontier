from __future__ import annotations
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _uuid() -> str:
    return str(uuid.uuid4())


@dataclass
class Budget:
    cost_limit_tokens: Optional[int] = None
    time_limit_ms: Optional[int] = None


@dataclass
class Envelope:
    schema_version: str = "1.0"
    id: str = field(default_factory=_uuid)
    correlation_id: str = field(default_factory=_uuid)
    causality: Optional[str] = None
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    msg_type: str = "unknown"
    sender: str = "unknown"
    topic: str = "general"
    tags: List[str] = field(default_factory=list)
    budget: Budget = field(default_factory=Budget)
    payload: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_json(self) -> str:
        def _enc(o: Any):
            if isinstance(o, Budget):
                return o.__dict__
            if isinstance(o, Envelope):
                d = o.__dict__.copy()
                d["budget"] = _enc(o.budget)
                return d
            raise TypeError()

        return json.dumps(_enc(self))

    @staticmethod
    def from_json(s: str) -> "Envelope":
        d = json.loads(s)
        b = d.get("budget") or {}
        d["budget"] = Budget(**b)
        return Envelope(**d)
