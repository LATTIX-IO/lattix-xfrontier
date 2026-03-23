from __future__ import annotations
from typing import Callable

from .contracts import Envelope
from .security import runtime_security_middleware
from .validation import validate_envelope_dict


def envelope_validator(strict: bool = False) -> Callable[[Envelope], None]:
    """Validates the envelope shape. In strict mode, raises on errors; otherwise appends errors."""

    def _mw(env: Envelope) -> None:
        errors = validate_envelope_dict({
            "schema_version": env.schema_version,
            "id": env.id,
            "correlation_id": env.correlation_id,
            "causality": env.causality,
            "created_at_ms": env.created_at_ms,
            "msg_type": env.msg_type,
            "sender": env.sender,
            "topic": env.topic,
            "tags": env.tags,
            "budget": {
                "cost_limit_tokens": env.budget.cost_limit_tokens,
                "time_limit_ms": env.budget.time_limit_ms,
            }
            if env.budget
            else None,
            "payload": env.payload,
            "errors": env.errors,
        })
        if errors:
            if strict:
                raise ValueError("envelope validation failed: " + "; ".join(errors))
            env.errors.extend(errors)

    return _mw


def attach_default_middlewares(bus, strict: bool = False) -> None:
    """Attach default middlewares to the bus (validation now; extend as needed)."""
    bus.use(envelope_validator(strict=strict))
    bus.use(runtime_security_middleware())

