"""Universal envelope contract used across workflows, APIs, and agents."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _is_json_compatible(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(_is_json_compatible(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_compatible(item) for key, item in value.items())
    return False


class EnvelopeStatus(str, Enum):
    """Lifecycle states for an envelope."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"


class Budget(BaseModel):
    """Budget constraints and current consumption for a unit of work."""

    model_config = ConfigDict(extra="forbid")

    max_tokens: int = 100_000
    max_duration_seconds: int = 300
    max_cost_usd: float = 1.0
    tokens_used: int = 0
    duration_used_seconds: float = 0.0
    cost_used_usd: float = 0.0

    def has_remaining_capacity(self) -> bool:
        """Return whether the budget is still within all limits."""

        return (
            self.tokens_used <= self.max_tokens
            and self.duration_used_seconds <= self.max_duration_seconds
            and self.cost_used_usd <= self.max_cost_usd
        )


class Envelope(BaseModel):
    """Typed message contract for orchestration, A2A, events, and API surfaces."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_agent: str
    target_agent: str | None = None
    workflow_id: str | None = None
    action: str
    payload: dict[str, Any]
    tags: list[str] = Field(default_factory=list)
    status: EnvelopeStatus = EnvelopeStatus.PENDING
    budget: Budget = Field(default_factory=Budget)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    capability_token: str | None = None

    @field_validator("source_agent", "action")
    @classmethod
    def _require_non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            msg = "must not be blank"
            raise ValueError(msg)
        return cleaned

    @field_validator("payload", "metadata")
    @classmethod
    def _validate_json_compatible_mapping(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not _is_json_compatible(value):
            msg = "must contain only JSON-compatible values"
            raise ValueError(msg)
        return value
