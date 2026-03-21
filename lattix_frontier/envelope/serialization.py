"""Serialization helpers for the universal envelope contract."""

from __future__ import annotations

import json

from lattix_frontier.envelope.models import Envelope


def envelope_to_json(envelope: Envelope) -> str:
    """Serialize an envelope to canonical JSON."""

    return envelope.model_dump_json()


def envelope_from_json(payload: str) -> Envelope:
    """Deserialize an envelope from JSON text."""

    return Envelope.model_validate(json.loads(payload))


def envelope_to_protobuf_bytes(envelope: Envelope) -> bytes:
    """Serialize an envelope to bytes.

    TODO(owner=platform, reason=replace JSON transport shim with a protobuf schema).
    """

    return envelope_to_json(envelope).encode("utf-8")


def envelope_from_protobuf_bytes(payload: bytes) -> Envelope:
    """Deserialize an envelope from bytes.

    TODO(owner=platform, reason=replace JSON transport shim with true protobuf decoding).
    """

    return envelope_from_json(payload.decode("utf-8"))
