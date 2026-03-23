from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

import jwt

from frontier_runtime.persistence import load_state, mutate_state


def _secret_bytes(key: bytes | str | None = None) -> bytes:
    if isinstance(key, bytes):
        return key
    if isinstance(key, str) and key:
        return key.encode("utf-8")
    return str(os.getenv("A2A_JWT_SECRET", "unit-test-super-secret-value-32bytes")).encode("utf-8")


def build_default_keypair() -> bytes:
    return _secret_bytes()


@dataclass(frozen=True)
class CapabilityClaims:
    agent_id: str
    allowed_tools: list[str]
    allowed_read_paths: list[str]
    allowed_write_paths: list[str]
    max_tool_calls: int


class CapabilityMinter:
    def __init__(self, keypair: bytes | str) -> None:
        self._key = _secret_bytes(keypair)

    def mint_agent_token(
        self,
        agent_id: str,
        allowed_tools: list[str],
        allowed_read_paths: list[str],
        allowed_write_paths: list[str],
        max_tool_calls: int,
    ) -> bytes:
        payload = {
            "agent_id": agent_id,
            "allowed_tools": allowed_tools,
            "allowed_read_paths": allowed_read_paths,
            "allowed_write_paths": allowed_write_paths,
            "max_tool_calls": max_tool_calls,
        }
        payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signature = hmac.new(self._key, payload_bytes, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(payload_bytes) + b"." + base64.urlsafe_b64encode(signature)


class CapabilityVerifier:
    def __init__(self, keypair: bytes | str) -> None:
        self._key = _secret_bytes(keypair)

    def verify(self, token: bytes | str, action: str, agent_id: str) -> bool:
        raw = token.encode("utf-8") if isinstance(token, str) else token
        try:
            encoded_payload, encoded_sig = raw.split(b".", 1)
            payload_bytes = base64.urlsafe_b64decode(encoded_payload)
            expected_sig = hmac.new(self._key, payload_bytes, hashlib.sha256).digest()
            actual_sig = base64.urlsafe_b64decode(encoded_sig)
            if not hmac.compare_digest(expected_sig, actual_sig):
                return False
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            return False
        return payload.get("agent_id") == agent_id and action in (payload.get("allowed_tools") or [])


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class OPAClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    @staticmethod
    def _path_allowed(candidate: str, allowed_paths: list[str]) -> bool:
        value = str(candidate or "").strip()
        if not value:
            return False
        try:
            resolved_candidate = Path(value).expanduser().resolve(strict=False)
        except Exception:
            return False

        for item in allowed_paths:
            root = str(item or "").strip()
            if not root:
                continue
            try:
                resolved_root = Path(root).expanduser().resolve(strict=False)
            except Exception:
                continue
            if resolved_candidate == resolved_root or resolved_candidate.is_relative_to(resolved_root):
                return True
        return False

    async def evaluate(self, policy_name: str, payload: dict[str, Any]) -> PolicyDecision:
        await asyncio.sleep(0)
        if policy_name == "agent_policy":
            budget = payload.get("budget") or {}
            tokens_used = int(budget.get("tokens_used", 0))
            max_tokens = int(budget.get("max_tokens", 0))
            if tokens_used > max_tokens:
                return PolicyDecision(False, "budget overrun")
            agent_id = str(payload.get("agent_id") or "")
            tool = str(payload.get("tool") or "")
            if agent_id in {"orchestrator", "backend"} and tool == "execute_step":
                return PolicyDecision(True, "allowed by local fallback")
            return PolicyDecision(False, "agent/tool not allowlisted")
        if policy_name == "network_egress":
            target = str(payload.get("target") or "")
            allowed_targets = {str(item) for item in payload.get("allowed_targets", [])}
            return PolicyDecision(target in allowed_targets, "target allowed" if target in allowed_targets else "target denied")
        if policy_name == "tool_jail":
            run_as_user = str(payload.get("run_as_user") or "")
            if run_as_user == "0:0":
                return PolicyDecision(False, "root execution denied")
            return PolicyDecision(True, "tool jail policy passed")
        if policy_name == "filesystem_path":
            action = str(payload.get("action") or "read").lower()
            target = str(payload.get("target_path") or payload.get("path") or "")
            if action.startswith("write"):
                allowed_paths = [str(item) for item in payload.get("allowed_write_paths", [])]
            elif action.startswith("read"):
                allowed_paths = [str(item) for item in payload.get("allowed_read_paths", [])]
            else:
                allowed_paths = [str(item) for item in payload.get("allowed_paths", [])]
            allowed = self._path_allowed(target, allowed_paths)
            return PolicyDecision(allowed, "path allowed" if allowed else "path denied")
        return PolicyDecision(False, "unknown policy")


class VaultClient:
    def read_secret(self, path: str) -> dict[str, Any]:
        return {"path": path, "value": "development-placeholder"}


def mint_token(sub: str, ttl_seconds: int = 600, additional_claims: dict[str, Any] | None = None) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "iat": now,
        "exp": now + ttl_seconds,
        "iss": "lattix-frontier",
        "aud": "frontier-runtime",
        "jti": str(uuid4()),
    }
    if additional_claims:
        payload.update(additional_claims)
    return str(jwt.encode(payload, _secret_bytes(), algorithm="HS256"))


def verify_token(token: str, require_nonce: bool = True) -> dict[str, Any]:
    claims = jwt.decode(
        token,
        _secret_bytes(),
        algorithms=["HS256"],
        audience="frontier-runtime",
        issuer="lattix-frontier",
    )
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    state = load_state()
    replay_tokens = set(str(item) for item in state.get("replay_tokens", []))
    if token_hash in replay_tokens:
        raise ValueError("replay detected")

    def _mutate(snapshot: dict[str, Any]) -> None:
        tokens = [str(item) for item in snapshot.get("replay_tokens", [])]
        if token_hash not in tokens:
            tokens.append(token_hash)
        snapshot["replay_tokens"] = tokens[-5000:]

    mutate_state(_mutate)
    return claims


def reset_token_caches() -> None:
    return None


def sign_event(event: Any) -> str:
    message = f"{getattr(event, 'event_hash', '')}:{getattr(event, 'source', '')}"
    return hmac.new(_secret_bytes(), message.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_event_signature(event: Any) -> bool:
    expected = sign_event(event)
    actual = str(getattr(event, "signature", ""))
    return bool(actual) and hmac.compare_digest(actual, expected)
