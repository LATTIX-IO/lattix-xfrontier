"""Shared pytest fixtures for Frontier tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

LEGACY_PACKAGE_AVAILABLE = importlib.util.find_spec("lattix_frontier") is not None

if LEGACY_PACKAGE_AVAILABLE:
    from lattix_frontier.api.app import create_app
    from lattix_frontier.config import get_settings
    from lattix_frontier.events.nats_client import reset_event_bus
    from lattix_frontier.orchestrator.approvals import reset_approval_store
    from lattix_frontier.persistence.state_backend import reset_shared_state_backend
    from lattix_frontier.security.jwt_auth import mint_token
    from lattix_frontier.security.jwt_auth import reset_token_caches


def pytest_ignore_collect(collection_path: Path, path: object | None = None, config: object | None = None) -> bool:
    if LEGACY_PACKAGE_AVAILABLE:
        return False
    return True


@pytest.fixture(autouse=True)
def security_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    if not LEGACY_PACKAGE_AVAILABLE:
        pytest.skip("legacy lattix_frontier test suite is disabled because the legacy package is not installed")
    monkeypatch.setenv("A2A_JWT_SECRET", "unit-test-super-secret-value")
    monkeypatch.setenv("A2A_TRUSTED_SUBJECTS", "orchestrator,research,code,review,coordinator,test-admin")
    monkeypatch.setenv("ALLOWED_EGRESS_HOSTS", "api.example.com,localhost,127.0.0.1")
    monkeypatch.setenv("FRONTIER_STATE_STORE", str(tmp_path / "frontier-state.db"))
    get_settings.cache_clear()
    reset_shared_state_backend()
    reset_approval_store()
    reset_event_bus()
    reset_token_caches()
    yield
    reset_shared_state_backend()
    reset_approval_store()
    reset_event_bus()
    reset_token_caches()
    get_settings.cache_clear()


@pytest.fixture()
def test_client() -> TestClient:
    if not LEGACY_PACKAGE_AVAILABLE:
        pytest.skip("legacy lattix_frontier test suite is disabled because the legacy package is not installed")
    return TestClient(create_app())


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    if not LEGACY_PACKAGE_AVAILABLE:
        pytest.skip("legacy lattix_frontier test suite is disabled because the legacy package is not installed")
    token = mint_token("test-admin", ttl_seconds=60, additional_claims={"token_use": "admin"})
    return {"Authorization": f"Bearer {token}"}
