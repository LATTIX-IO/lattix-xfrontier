"""Validation helpers for envelope schema and contract checks."""

from __future__ import annotations

from lattix_frontier.envelope.models import Envelope


def validate_envelope(envelope: Envelope) -> Envelope:
    """Return a validated envelope instance."""

    return Envelope.model_validate(envelope.model_dump())


def ensure_budget_available(envelope: Envelope) -> None:
    """Raise an error if an envelope budget has been exhausted."""

    if not envelope.budget.has_remaining_capacity():
        msg = f"budget exhausted for envelope {envelope.id}"
        raise ValueError(msg)
