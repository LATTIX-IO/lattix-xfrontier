import asyncio
from pathlib import Path

from lattix_frontier.events.event_models import AgentEvent
from lattix_frontier.events.nats_client import get_event_bus, reset_event_bus
from lattix_frontier.orchestrator.approvals import get_approval_store, reset_approval_store
from lattix_frontier.persistence.state_backend import reset_shared_state_backend
from lattix_frontier.security.jwt_auth import mint_token, reset_token_caches, verify_token


def test_approval_store_persists_across_singleton_reset(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FRONTIER_STATE_STORE", str(tmp_path / "state.db"))
    reset_shared_state_backend()
    reset_approval_store()

    created = get_approval_store().create("confidential", "approve me")

    reset_shared_state_backend()
    reset_approval_store()
    restored = get_approval_store().get(created.id)

    assert restored is not None
    assert restored.task == "approve me"
    assert restored.status == "pending"


def test_event_bus_fallback_persists_events_across_singleton_reset(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FRONTIER_STATE_STORE", str(tmp_path / "state.db"))
    reset_shared_state_backend()
    reset_event_bus()

    bus = get_event_bus()
    published = asyncio.run(bus.publish(AgentEvent(event_type="demo", source="tester")))

    reset_shared_state_backend()
    reset_event_bus()
    reloaded = get_event_bus().fallback.list_events()

    assert reloaded
    assert reloaded[-1].id == published.id
    assert reloaded[-1].event_hash == published.event_hash


def test_replay_cache_persists_across_singleton_reset(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FRONTIER_STATE_STORE", str(tmp_path / "state.db"))
    reset_shared_state_backend()
    reset_token_caches()

    token = mint_token("orchestrator", ttl_seconds=60)
    verify_token(token, require_nonce=False)

    reset_shared_state_backend()
    reset_token_caches()

    try:
        verify_token(token, require_nonce=False)
    except ValueError as exc:
        assert "replay detected" in str(exc)
    else:  # pragma: no cover - safety net
        raise AssertionError("expected replay detection after cache reset")