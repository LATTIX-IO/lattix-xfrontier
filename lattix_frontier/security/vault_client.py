"""Vault client wrapper."""

from __future__ import annotations

from typing import Any

import requests

from lattix_frontier.config import get_settings

try:
    import hvac
except ImportError:  # pragma: no cover
    hvac = None  # type: ignore[assignment]


class VaultClient:
    """Minimal Vault wrapper supporting local dev token auth."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = None if hvac is None else hvac.Client(url=settings.vault_addr, token=settings.vault_token)

    def is_available(self) -> bool:
        return self._client is not None

    def read_secret(self, path: str) -> dict[str, Any]:
        settings = get_settings()
        if self._client is None:
            if settings.app_env.lower() in {"development", "dev", "test", "local"}:
                return {"path": path, "value": "development-placeholder"}
            raise RuntimeError("Vault client unavailable outside development/test environments")
        try:
            response = self._client.secrets.kv.v2.read_secret_version(path=path)
        except Exception:
            if settings.app_env.lower() in {"development", "dev", "test", "local"}:
                return {"path": path, "value": "development-placeholder"}
            raise RuntimeError(f"Vault unavailable while reading secret at {path}")
        return dict(response["data"]["data"])
