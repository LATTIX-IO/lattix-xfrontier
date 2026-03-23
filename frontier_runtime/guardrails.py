from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any

from frontier_runtime.envelope import Envelope
from frontier_runtime.security import CapabilityVerifier, build_default_keypair


@dataclass(frozen=True)
class FilterContext:
    classification: str = "internal"


@dataclass
class FilterResult:
    action: str
    envelope: Envelope
    reason: str = ""


class DLPFilter:
    async def evaluate(self, envelope: Envelope, context: FilterContext) -> FilterResult:
        mutated = copy.deepcopy(envelope)
        findings: list[str] = []
        for key, value in list(mutated.payload.items()):
            if isinstance(value, str):
                redacted, value_findings = _redact_sensitive_text(value)
                if redacted != value:
                    mutated.payload[key] = redacted
                findings.extend(value_findings)
        if findings:
            mutated.metadata["classification"] = "restricted" if "credit_card" in findings else "confidential"
            mutated.metadata["dlp_findings"] = findings
            return FilterResult(action="modify", envelope=mutated)
        mutated.metadata.setdefault("classification", context.classification)
        return FilterResult(action="pass", envelope=mutated)


class PromptRenderFilter:
    async def evaluate(self, envelope: Envelope, context: FilterContext) -> FilterResult:
        mutated = copy.deepcopy(envelope)
        mutated.payload["frontier_policy_context"] = {"classification": context.classification}
        return FilterResult(action="modify", envelope=mutated)


class _DefaultFilterChain:
    async def run(self, envelope: Envelope, context: FilterContext) -> FilterResult:
        if envelope.target_agent and envelope.action == "execute_step":
            token = envelope.capability_token
            if not token:
                return FilterResult(action="block", envelope=envelope, reason="capability token required")
            verifier = CapabilityVerifier(build_default_keypair())
            if not verifier.verify(token, envelope.action, envelope.target_agent):
                return FilterResult(action="block", envelope=envelope, reason="invalid capability token")
        return FilterResult(action="pass", envelope=envelope)


def default_filter_chain() -> _DefaultFilterChain:
    return _DefaultFilterChain()


def _redact_sensitive_text(text: str) -> tuple[str, list[str]]:
    redacted = text
    findings: list[str] = []
    patterns = [
        ("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[REDACTED_EMAIL]"),
        ("phone", r"\b(?:\+?\d{1,2}\s*)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}\b", "[REDACTED_PHONE]"),
        ("credit_card", r"\b(?:\d[ -]*?){13,16}\b", "[REDACTED_CREDIT_CARD]"),
        ("password", r"(?i)(password\s*[=:]\s*)([^\s,;]+)", r"\1[REDACTED_PASSWORD]"),
    ]
    for finding, pattern, replacement in patterns:
        updated = re.sub(pattern, replacement, redacted)
        if updated != redacted:
            findings.append(finding)
            redacted = updated
    return redacted, findings
