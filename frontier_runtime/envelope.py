from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class EnvelopeStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    BLOCKED = "blocked"


@dataclass
class Envelope:
    source_agent: str
    action: str
    payload: dict[str, Any]
    target_agent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    capability_token: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    status: EnvelopeStatus = EnvelopeStatus.PENDING


def envelope_to_json(envelope: Envelope) -> str:
    payload = asdict(envelope)
    payload["status"] = envelope.status.value
    return json.dumps(payload)


def envelope_from_json(text: str) -> Envelope:
    payload = json.loads(text)
    status = EnvelopeStatus(str(payload.get("status", EnvelopeStatus.PENDING.value)))
    payload["status"] = status
    return Envelope(**payload)
