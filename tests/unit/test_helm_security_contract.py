from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_helm_values_default_to_hosted_runtime_profile() -> None:
    values = _read("helm/lattix-frontier/values.yaml")
    values_prod = _read("helm/lattix-frontier/values-prod.yaml")

    assert "profile: hosted" in values
    assert "requireA2ARuntimeHeaders: true" in values
    assert "profile: hosted" in values_prod
    assert "requireA2ARuntimeHeaders: true" in values_prod


def test_helm_api_and_orchestrator_propagate_runtime_security_env() -> None:
    api_deployment = _read("helm/lattix-frontier/templates/deployment-api.yaml")
    orchestrator_deployment = _read("helm/lattix-frontier/templates/deployment-orchestrator.yaml")

    for template in (api_deployment, orchestrator_deployment):
        assert "name: FRONTIER_RUNTIME_PROFILE" in template
        assert "name: FRONTIER_REQUIRE_A2A_RUNTIME_HEADERS" in template
        assert "name: A2A_JWT_SECRET" in template
        assert "secretKeyRef:" in template


def test_helm_network_policy_targets_control_plane_workloads() -> None:
    network_policies = _read("helm/lattix-frontier/templates/network-policies.yaml")

    assert "name: lattix-control-plane-default-deny" in network_policies
    assert "app: lattix-api" in network_policies
    assert "app: lattix-orchestrator" in network_policies
    assert "app: lattix-envoy" in network_policies