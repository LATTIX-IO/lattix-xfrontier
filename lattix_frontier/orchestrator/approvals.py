"""Approval request registry for human-in-the-loop workflow gates."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
import uuid

from pydantic import BaseModel, Field

from lattix_frontier.persistence.state_backend import get_shared_state_backend


class ApprovalRequest(BaseModel):
    """Approval request persisted for polling and decisions."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    classification: str
    task: str
    status: str = "pending"
    decision: str | None = None


class ApprovalStore:
    """SQLite-backed approval store for workflow approval persistence."""

    def __init__(self) -> None:
        self._backend = get_shared_state_backend()
        self._lock = Lock()

    def create(self, classification: str, task: str) -> ApprovalRequest:
        request = ApprovalRequest(classification=classification, task=task)
        with self._lock:
            self._backend.put_approval(
                request.id,
                request.created_at.isoformat(),
                request.classification,
                request.task,
                request.status,
                request.decision,
            )
        return request

    def get(self, approval_id: str) -> ApprovalRequest | None:
        with self._lock:
            row = self._backend.get_approval(approval_id)
        if row is None:
            return None
        return ApprovalRequest(
            id=str(row[0]),
            created_at=datetime.fromisoformat(str(row[1])),
            classification=str(row[2]),
            task=str(row[3]),
            status=str(row[4]),
            decision=None if row[5] is None else str(row[5]),
        )

    def decide(self, approval_id: str, decision: str) -> ApprovalRequest:
        with self._lock:
            row = self._backend.get_approval(approval_id)
            if row is None:
                raise KeyError(approval_id)
            request = ApprovalRequest(
                id=str(row[0]),
                created_at=datetime.fromisoformat(str(row[1])),
                classification=str(row[2]),
                task=str(row[3]),
                status=str(row[4]),
                decision=None if row[5] is None else str(row[5]),
            )
            self._backend.put_approval(
                request.id,
                request.created_at.isoformat(),
                request.classification,
                request.task,
                decision,
                decision,
            )
            request.status = decision
            request.decision = decision
        return request


_approval_store: ApprovalStore | None = None


def get_approval_store() -> ApprovalStore:
    global _approval_store
    if _approval_store is None:
        _approval_store = ApprovalStore()
    return _approval_store


def reset_approval_store() -> None:
    """Reset the approval store singleton for tests or config reloads."""

    global _approval_store
    _approval_store = None