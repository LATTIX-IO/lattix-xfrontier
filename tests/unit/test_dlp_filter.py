import asyncio

from lattix_frontier.envelope.models import Envelope
from lattix_frontier.guardrails.filter_chain import FilterContext
from lattix_frontier.guardrails.filters.dlp_filter import DLPFilter


def test_dlp_filter_marks_pii() -> None:
    envelope = Envelope(source_agent="tester", action="execute", payload={"task": "email me at test@example.com"})
    result = asyncio.run(DLPFilter().evaluate(envelope, FilterContext()))
    assert result.envelope.metadata["classification"] in {"internal", "confidential", "restricted"}
    assert result.envelope.payload["task"] == "email me at [REDACTED_EMAIL]"


def test_dlp_filter_redacts_multiple_secret_patterns() -> None:
    envelope = Envelope(
        source_agent="tester",
        action="execute",
        payload={
            "task": "call me at 555-222-1212 with card 4111 1111 1111 1111 and password=hunter2",
        },
    )

    result = asyncio.run(DLPFilter().evaluate(envelope, FilterContext()))

    assert result.action == "modify"
    assert "phone" in str(result.envelope.metadata.get("dlp_findings", ""))
    assert "credit_card" in str(result.envelope.metadata.get("dlp_findings", ""))
    assert "password" in str(result.envelope.metadata.get("dlp_findings", ""))
    assert "[REDACTED_PHONE]" in str(result.envelope.payload["task"])
    assert "[REDACTED_CREDIT_CARD]" in str(result.envelope.payload["task"])
    assert "[REDACTED_PASSWORD]" in str(result.envelope.payload["task"])
