from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_secure_local_compose_includes_casdoor_service_and_oidc_envs() -> None:
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "casdoor:" in compose
    assert "casbin/casdoor-all-in-one" in compose
    assert "FRONTIER_AUTH_OIDC_ISSUER: ${FRONTIER_AUTH_OIDC_ISSUER:-http://casdoor.localhost}" in compose
    assert "FRONTIER_ADMIN_ACTORS: ${FRONTIER_ADMIN_ACTORS:-frontier-admin,admin@frontier.localhost}" in compose
    assert "FRONTIER_BUILDER_ACTORS: ${FRONTIER_BUILDER_ACTORS:-frontier-admin,admin@frontier.localhost}" in compose


def test_local_gateway_routes_casdoor_host() -> None:
    caddyfile = (REPO_ROOT / "docker" / "local" / "Caddyfile").read_text(encoding="utf-8")

    assert "http://{$CASDOOR_LOCAL_HOST:casdoor.localhost}" in caddyfile
    assert "reverse_proxy casdoor:8000" in caddyfile