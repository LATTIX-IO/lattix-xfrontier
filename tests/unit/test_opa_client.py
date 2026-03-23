import asyncio

from frontier_runtime.security import OPAClient


def test_opa_client_local_fallback_denies_budget_overrun() -> None:
    client = OPAClient(base_url="http://127.0.0.1:9")
    decision = asyncio.run(
        client.evaluate(
            "agent_policy",
            {"budget": {"tokens_used": 2, "max_tokens": 1}, "classification": "internal", "provider": "local"},
        )
    )
    assert decision.allowed is False


def test_opa_client_local_agent_policy_allows_backend_execute_step() -> None:
    client = OPAClient(base_url="http://127.0.0.1:9")
    decision = asyncio.run(
        client.evaluate(
            "agent_policy",
            {
                "agent_id": "backend",
                "tool": "execute_step",
                "resource": "research",
                "budget": {"tokens_used": 0, "max_tokens": 10},
                "classification": "internal",
                "provider": "local",
            },
        )
    )
    assert decision.allowed is True


def test_opa_client_local_fallback_denies_unallowlisted_egress() -> None:
    client = OPAClient(base_url="http://127.0.0.1:9")
    decision = asyncio.run(
        client.evaluate(
            "network_egress",
            {"action": "network_egress", "target": "evil.example.com", "allowed_targets": ["api.example.com"]},
        )
    )
    assert decision.allowed is False


def test_opa_client_local_fallback_denies_root_tool_jail() -> None:
    client = OPAClient(base_url="http://127.0.0.1:9")
    decision = asyncio.run(
        client.evaluate(
            "tool_jail",
            {
                "readonly_rootfs": True,
                "require_egress_mediation": True,
                "allow_network": False,
                "run_as_user": "0:0",
            },
        )
    )
    assert decision.allowed is False


def test_opa_client_filesystem_path_policy_uses_canonical_containment(tmp_path) -> None:
    client = OPAClient(base_url="http://127.0.0.1:9")
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    target = allowed_root / "nested" / "artifact.txt"
    target.parent.mkdir()
    target.write_text("ok", encoding="utf-8")

    decision = asyncio.run(
        client.evaluate(
            "filesystem_path",
            {"action": "read", "target_path": str(target), "allowed_read_paths": [str(allowed_root)]},
        )
    )

    assert decision.allowed is True


def test_opa_client_filesystem_path_policy_denies_prefix_bypass(tmp_path) -> None:
    client = OPAClient(base_url="http://127.0.0.1:9")
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    target = tmp_path / "allowed-evil" / "artifact.txt"
    target.parent.mkdir()
    target.write_text("nope", encoding="utf-8")

    decision = asyncio.run(
        client.evaluate(
            "filesystem_path",
            {"action": "read", "target_path": str(target), "allowed_read_paths": [str(allowed_root)]},
        )
    )

    assert decision.allowed is False

