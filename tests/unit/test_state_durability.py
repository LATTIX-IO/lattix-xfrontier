import asyncio
from pathlib import Path

from frontier_runtime.events import AgentEvent, get_event_bus, reset_event_bus
from frontier_runtime.orchestrator import get_approval_store, reset_approval_store
from frontier_runtime.persistence import reset_shared_state_backend
from frontier_runtime.security import decode_token, mint_token, reset_token_caches, token_identity_from_claims, verify_token


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


def test_decode_token_preserves_identity_claims_without_consuming_replay_cache(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FRONTIER_STATE_STORE", str(tmp_path / "state.db"))
    reset_shared_state_backend()
    reset_token_caches()

    token = mint_token(
        "member-user",
        ttl_seconds=60,
        additional_claims={
            "actor": "member-user",
            "tenant_id": "acme",
            "internal_service": False,
        },
    )

    claims = decode_token(token)
    identity = token_identity_from_claims(claims)

    assert identity.actor == "member-user"
    assert identity.subject == "member-user"
    assert identity.tenant_id == "acme"

    verify_token(token, require_nonce=False)