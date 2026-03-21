"""Simple content classification helpers."""

from __future__ import annotations

import re


def classify_payload_text(text: str) -> str:
    """Classify payload text sensitivity using lightweight heuristics."""

    if re.search(r"\b(ssn|password|secret|private key)\b", text, re.IGNORECASE):
        return "restricted"
    if re.search(r"\b(email|phone|customer|employee)\b", text, re.IGNORECASE):
        return "confidential"
    return "internal"
