"""DLP filter using regex plus optional Presidio/GLiNER hooks."""

from __future__ import annotations

import re
from typing import Any

try:
    from presidio_analyzer import AnalyzerEngine
except ImportError:  # pragma: no cover - optional in constrained environments.
    AnalyzerEngine = None  # type: ignore[assignment]

from lattix_frontier.guardrails.content_classifier import classify_payload_text
from lattix_frontier.guardrails.filter_chain import Filter, FilterContext, FilterResult

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
PHONE_RE = re.compile(r"\b(?:\+?\d{1,2}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}\b")
API_KEY_RE = re.compile(r"\b(?:sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,})\b")
PASSWORD_RE = re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*\S+")


def _redact_string(value: str, findings: list[str]) -> str:
    redacted = value
    replacements = [
        (EMAIL_RE, "email", "[REDACTED_EMAIL]"),
        (SSN_RE, "ssn", "[REDACTED_SSN]"),
        (CREDIT_CARD_RE, "credit_card", "[REDACTED_CREDIT_CARD]"),
        (PHONE_RE, "phone", "[REDACTED_PHONE]"),
        (API_KEY_RE, "api_key", "[REDACTED_API_KEY]"),
        (PASSWORD_RE, "password", "[REDACTED_PASSWORD]"),
    ]
    for pattern, finding, replacement in replacements:
        if pattern.search(redacted):
            if finding not in findings:
                findings.append(finding)
            redacted = pattern.sub(replacement, redacted)
    return redacted


def _redact_value(value: Any, findings: list[str]) -> Any:
    if isinstance(value, str):
        return _redact_string(value, findings)
    if isinstance(value, list):
        return [_redact_value(item, findings) for item in value]
    if isinstance(value, dict):
        return {str(key): _redact_value(item, findings) for key, item in value.items()}
    return value


class DLPFilter(Filter):
    """Detect basic PII and mark/classify the envelope."""

    _analyzer: AnalyzerEngine | None = AnalyzerEngine() if AnalyzerEngine is not None else None

    async def evaluate(self, envelope, context: FilterContext) -> FilterResult:  # type: ignore[override]
        payload_text = " ".join(str(value) for value in envelope.payload.values())
        findings: list[str] = []
        redacted_payload = _redact_value(dict(envelope.payload), findings)
        redacted_text = " ".join(str(value) for value in redacted_payload.values())
        if self._analyzer is not None:
            presidio_results = self._analyzer.analyze(text=payload_text, language="en")
            for result in presidio_results:
                finding = str(result.entity_type).lower()
                if finding not in findings:
                    findings.append(finding)
        classification = classify_payload_text(redacted_text)
        metadata = dict(envelope.metadata)
        metadata["classification"] = classification
        if findings:
            metadata["dlp_findings"] = ",".join(findings)
            updated = envelope.model_copy(update={"metadata": metadata, "payload": redacted_payload})
            return FilterResult(action="modify", envelope=updated, reason="pii redacted")
        return FilterResult(action="pass", envelope=envelope.model_copy(update={"metadata": metadata}))
