"""JWT helpers for A2A and admin API authentication."""

from __future__ import annotations

import time
from threading import Lock
from typing import Any
from uuid import uuid4

import jwt

from lattix_frontier.config import get_settings
from lattix_frontier.persistence.state_backend import get_shared_state_backend


class _ReplayCache:
    def __init__(self) -> None:
        self._backend = get_shared_state_backend()
        self._lock = Lock()

    def check_and_store(self, key: str, ttl_seconds: int) -> bool:
        now = int(time.time())
        expires_at = now + max(1, ttl_seconds)
        with self._lock:
            self._backend.delete_expired_replay_keys(now)
            return self._backend.put_replay_key(key, expires_at)


class _RevocationCache:
    def __init__(self) -> None:
        self._backend = get_shared_state_backend()
        self._lock = Lock()

    def revoke(self, token_id: str, ttl_seconds: int) -> None:
        with self._lock:
            expires_at = int(time.time()) + max(1, ttl_seconds)
            self._backend.revoke_token(token_id, expires_at)

    def is_revoked(self, token_id: str) -> bool:
        now = int(time.time())
        with self._lock:
            return self._backend.is_token_revoked(token_id, now)


_REPLAY_CACHE: _ReplayCache | None = None
_REVOCATION_CACHE: _RevocationCache | None = None


def _get_replay_cache() -> _ReplayCache:
    global _REPLAY_CACHE
    if _REPLAY_CACHE is None:
        _REPLAY_CACHE = _ReplayCache()
    return _REPLAY_CACHE


def _get_revocation_cache() -> _RevocationCache:
    global _REVOCATION_CACHE
    if _REVOCATION_CACHE is None:
        _REVOCATION_CACHE = _RevocationCache()
    return _REVOCATION_CACHE


def reset_token_caches() -> None:
    """Reset JWT replay/revocation cache singletons for tests or config reloads."""

    global _REPLAY_CACHE, _REVOCATION_CACHE
    _REPLAY_CACHE = None
    _REVOCATION_CACHE = None


def _signing_material() -> tuple[str, str]:
    settings = get_settings()
    if settings.a2a_jwt_alg.startswith("HS"):
        if settings.a2a_jwt_secret is None:
            raise RuntimeError("A2A_JWT_SECRET is required for HS* algorithms")
        return settings.a2a_jwt_alg, settings.a2a_jwt_secret
    if settings.a2a_jwt_private_key is None:
        raise RuntimeError("A2A_JWT_PRIVATE_KEY is required for asymmetric algorithms")
    return settings.a2a_jwt_alg, settings.a2a_jwt_private_key


def _verification_material() -> tuple[str, str]:
    settings = get_settings()
    if settings.a2a_jwt_alg.startswith("HS"):
        if settings.a2a_jwt_secret is None:
            raise RuntimeError("A2A_JWT_SECRET is required for HS* verification")
        return settings.a2a_jwt_alg, settings.a2a_jwt_secret
    if settings.a2a_jwt_public_key is None:
        raise RuntimeError("A2A_JWT_PUBLIC_KEY is required for asymmetric verification")
    return settings.a2a_jwt_alg, settings.a2a_jwt_public_key


def mint_token(
    subject: str,
    ttl_seconds: int | None = None,
    nonce: str | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    now = int(time.time())
    payload: dict[str, Any] = {
        "iss": settings.a2a_jwt_issuer,
        "aud": settings.a2a_jwt_audience,
        "sub": subject,
        "iat": now,
        "exp": now + (ttl_seconds or settings.a2a_token_ttl_seconds),
        "jti": str(uuid4()),
    }
    if nonce:
        payload["nonce"] = nonce
    if additional_claims:
        payload.update(additional_claims)
    algorithm, key = _signing_material()
    return jwt.encode(payload, key, algorithm=algorithm)


def verify_token(
    token: str,
    nonce: str | None = None,
    *,
    enforce_replay: bool = True,
    require_nonce: bool | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    algorithm, key = _verification_material()
    claims = jwt.decode(
        token,
        key,
        algorithms=[algorithm],
        audience=settings.a2a_jwt_audience,
        issuer=settings.a2a_jwt_issuer,
        leeway=settings.a2a_clock_skew_seconds,
    )
    token_id = str(claims.get("jti") or "").strip()
    if token_id and _get_revocation_cache().is_revoked(token_id):
        raise ValueError("token has been revoked")
    subject = str(claims.get("sub") or "").strip()
    if settings.a2a_trusted_subjects and subject not in settings.a2a_trusted_subjects:
        raise ValueError("token subject is not trusted")
    should_require_nonce = settings.a2a_require_nonce if require_nonce is None else require_nonce
    expected_nonce = str(nonce or "").strip()
    claim_nonce = str(claims.get("nonce") or "").strip()
    if should_require_nonce:
        if not expected_nonce:
            raise ValueError("nonce is required but missing")
        if claim_nonce != expected_nonce:
            raise ValueError("nonce mismatch")
    if settings.a2a_replay_protection and enforce_replay:
        if not token_id:
            raise ValueError("token missing jti")
        expiry = int(claims.get("exp") or int(time.time()) + settings.a2a_replay_ttl_seconds)
        now = int(time.time())
        ttl = max(1, min(settings.a2a_replay_ttl_seconds, expiry - now + settings.a2a_clock_skew_seconds))
        if not _get_replay_cache().check_and_store(f"{subject}:{token_id}", ttl):
            raise ValueError("replay detected")
    return dict(claims)


def revoke_token(token: str) -> str:
    claims = verify_token(token, enforce_replay=False, require_nonce=False)
    token_id = str(claims.get("jti") or "").strip()
    if not token_id:
        raise ValueError("token missing jti")
    expiry = int(claims.get("exp") or int(time.time()) + get_settings().a2a_replay_ttl_seconds)
    ttl = max(1, expiry - int(time.time()))
    _get_revocation_cache().revoke(token_id, ttl)
    return token_id
