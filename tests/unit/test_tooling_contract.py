from pathlib import Path

from frontier_tooling.common import ensure_compose_env_file


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_compose_and_env_defaults_use_shared_runtime_audience() -> None:
    env_example = _read(".env.example")
    compose = _read("docker-compose.yml")
    tooling = _read("frontier_tooling/common.py")
    powershell = _read("scripts/frontier.ps1")

    assert "A2A_JWT_AUD=frontier-runtime" in env_example
    assert "A2A_JWT_AUD: ${A2A_JWT_AUD:-frontier-runtime}" in compose
    assert 'return "frontier-runtime"' in tooling
    assert '"frontier-runtime"' in powershell


def test_ci_and_local_tooling_expose_helm_validation() -> None:
    ci = _read(".github/workflows/ci.yml")
    makefile = _read("Makefile")
    powershell = _read("scripts/frontier.ps1")

    assert "azure/setup-helm" in ci
    assert "helm lint ./helm/lattix-frontier" in ci
    assert "helm template lattix ./helm/lattix-frontier -f helm/lattix-frontier/values-prod.yaml > /dev/null" in ci
    assert "helm-validate:" in makefile
    assert '"helm-validate"' in powershell


def test_bootstrap_installer_reports_secure_compose_env_path() -> None:
    installer = _read("frontier_tooling/installer.py")
    installer_docs = _read("docs/INSTALLER.md")

    assert 'ensure_compose_env_file(local_profile=False)' in installer
    assert '"compose_env": str(compose_env.resolve())' in installer
    assert ".installer/local-secure.env" in installer_docs
    assert ".installer/local-lightweight.env" in installer_docs


def test_compose_env_generation_uses_mode_specific_files_and_profiles() -> None:
    secure_env = ensure_compose_env_file(local_profile=False)
    lightweight_env = ensure_compose_env_file(local_profile=True)

    assert secure_env.name == "local-secure.env"
    assert lightweight_env.name == "local-lightweight.env"

    secure_text = secure_env.read_text(encoding="utf-8")
    lightweight_text = lightweight_env.read_text(encoding="utf-8")

    assert "FRONTIER_RUNTIME_PROFILE=local-secure" in secure_text
    assert "NEXT_PUBLIC_API_BASE_URL=/api" in secure_text
    assert "A2A_JWT_AUD=frontier-runtime" in secure_text

    assert "FRONTIER_RUNTIME_PROFILE=local-lightweight" in lightweight_text
    assert "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" in lightweight_text
    assert "A2A_JWT_AUD=frontier-runtime" in lightweight_text