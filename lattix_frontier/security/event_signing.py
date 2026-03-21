"""Event signing helpers for tamper-evident agent and orchestrator events."""

from __future__ import annotations

import hashlib
import hmac
import json

from lattix_frontier.config import get_settings
from lattix_frontier.events.event_models import AgentEvent


def _event_key_for_source(source: str) -> bytes:
    settings = get_settings()
    if source in settings.event_signing_keys:
        return settings.event_signing_keys[source].encode("utf-8")
    if settings.a2a_jwt_secret is None:
        raise RuntimeError("A2A_JWT_SECRET is required to derive per-source event signing keys")
    return hmac.new(settings.a2a_jwt_secret.encode("utf-8"), source.encode("utf-8"), hashlib.sha256).digest()


def sign_event(event: AgentEvent) -> AgentEvent:
    base = event.model_dump(mode="json", exclude={"signature", "signer"})
    payload = json.dumps(base, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(_event_key_for_source(event.source), payload, hashlib.sha256).hexdigest()
    return event.model_copy(update={"signer": event.source, "signature": signature})


def verify_event_signature(event: AgentEvent) -> bool:
    if not event.signature or not event.signer:
        return False
    base = event.model_dump(mode="json", exclude={"signature", "signer"})
    payload = json.dumps(base, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected = hmac.new(_event_key_for_source(event.signer), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(event.signature, expected)