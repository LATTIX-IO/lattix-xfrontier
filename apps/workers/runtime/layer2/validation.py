from __future__ import annotations
from typing import Any, Dict, List


REQUIRED_FIELDS = [
    "schema_version",
    "id",
    "correlation_id",
    "msg_type",
    "sender",
    "topic",
    "payload",
]


def validate_envelope_dict(env: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for f in REQUIRED_FIELDS:
        if f not in env:
            errors.append(f"missing field: {f}")
    # basic type checks
    if "payload" in env and not isinstance(env.get("payload"), dict):
        errors.append("payload must be an object")
    if "tags" in env and not isinstance(env.get("tags"), list):
        errors.append("tags must be an array")
    if "errors" in env and not isinstance(env.get("errors"), list):
        errors.append("errors must be an array")

    budget = env.get("budget")
    if budget is not None and not isinstance(budget, dict):
        errors.append("budget must be an object or null")

    return errors
