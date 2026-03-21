"""Scoped capability tokens backed by signed JWTs."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from lattix_frontier.security.jwt_auth import mint_token, verify_token


@dataclass
class KeyPair:
    """Compatibility wrapper around token configuration."""

    key_id: str = "default"


def build_default_keypair() -> KeyPair:
    """Build a default keypair placeholder."""

    return KeyPair()


class CapabilityMinter:
    """Mint scoped capability tokens."""

    def __init__(self, root_keypair: KeyPair) -> None:
        self.root_keypair = root_keypair

    def mint_agent_token(
        self,
        agent_id: str,
        allowed_tools: list[str],
        allowed_read_paths: list[str],
        allowed_write_paths: list[str],
        max_tool_calls: int,
        ttl_seconds: int = 300,
    ) -> bytes:
        claims: dict[str, Any] = {
            "allowed_tools": allowed_tools,
            "allowed_read_paths": allowed_read_paths,
            "allowed_write_paths": allowed_write_paths,
            "max_tool_calls": max_tool_calls,
            "token_use": "capability",
        }
        return mint_token(agent_id, ttl_seconds=ttl_seconds, additional_claims=claims).encode("utf-8")

    def attenuate(self, token: bytes, restrictions: dict[str, Any]) -> bytes:
        claims = inspect_token(token)
        claims.update(restrictions)
        agent_id = str(claims.get("sub") or claims.get("agent_id") or "")
        ttl_seconds = max(1, int(claims.get("exp", int(time.time()) + 30)) - int(time.time()))
        return mint_token(agent_id, ttl_seconds=ttl_seconds, additional_claims=claims).encode("utf-8")


class CapabilityVerifier:
    """Verify capability tokens at enforcement points."""

    def __init__(self, root_keypair: KeyPair) -> None:
        self.root_keypair = root_keypair

    def verify(self, token: bytes, requested_action: str, resource: str) -> bool:
        try:
            claims = inspect_token(token)
        except ValueError:
            return False
        if claims.get("token_use") != "capability":
            return False
        if int(claims.get("exp", 0)) < int(time.time()):
            return False
        subject = str(claims.get("sub") or "").strip()
        if subject and resource and subject != resource:
            return False
        allowed_tools = set(claims.get("allowed_tools", []))
        if requested_action not in allowed_tools:
            return False
        return bool(resource)


def inspect_token(token: bytes | str) -> dict[str, Any]:
    token_text = token.decode("utf-8") if isinstance(token, bytes) else token
    return verify_token(token_text, require_nonce=False, enforce_replay=False)
