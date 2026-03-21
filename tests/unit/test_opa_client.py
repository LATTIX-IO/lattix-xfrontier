import asyncio

from lattix_frontier.security.opa_client import OPAClient


def test_opa_client_local_fallback_denies_budget_overrun() -> None:
    client = OPAClient(base_url="http://127.0.0.1:9")
    decision = asyncio.run(
        client.evaluate(
            "agent_policy",
            {"budget": {"tokens_used": 2, "max_tokens": 1}, "classification": "internal", "provider": "local"},
        )
    )
    assert decision.allowed is False


def test_opa_client_local_agent_policy_allows_orchestrator_execute_step() -> None:
    client = OPAClient(base_url="http://127.0.0.1:9")
    decision = asyncio.run(
        client.evaluate(
            "agent_policy",
            {
                "agent_id": "orchestrator",
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

