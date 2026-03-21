"""Agent event schema."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from pydantic import BaseModel, Field


class AgentEvent(BaseModel):
    """Recorded agent or orchestrator event."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: str
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)
    signer: str | None = None
    signature: str | None = None
    prev_hash: str = "genesis"
    event_hash: str = ""
