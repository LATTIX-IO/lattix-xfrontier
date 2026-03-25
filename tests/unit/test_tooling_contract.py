from pathlib import Path

from frontier_tooling.common import ensure_compose_env_file, remove_installer_env_files


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
    assert ".installer/local-lightweight.env" not in installer_docs


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


def test_compose_env_generation_repairs_blank_a2a_secret(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("frontier_tooling.common.REPO_ROOT", tmp_path)
    monkeypatch.setattr("frontier_tooling.common.INSTALLER_DIR", tmp_path / ".installer")
    monkeypatch.setattr(
        "frontier_tooling.common.SECURE_INSTALLER_ENV_PATH",
        tmp_path / ".installer" / "local-secure.env",
    )
    monkeypatch.setattr(
        "frontier_tooling.common.LIGHTWEIGHT_INSTALLER_ENV_PATH",
        tmp_path / ".installer" / "local-lightweight.env",
    )

    (tmp_path / ".env").write_text("A2A_JWT_SECRET=from-dot-env\n", encoding="utf-8")
    (tmp_path / ".installer").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".installer" / "local-secure.env").write_text("A2A_JWT_SECRET=\n", encoding="utf-8")

    secure_env = ensure_compose_env_file(local_profile=False)
    secure_text = secure_env.read_text(encoding="utf-8")

    assert "A2A_JWT_SECRET=" in secure_text
    assert "A2A_JWT_SECRET=\n" not in secure_text


def test_tooling_and_docs_remove_dev_alias_but_keep_local_stack() -> None:
    readme = _read("README.md")
    deployment = _read("docs/DEPLOYMENT.md")
    contributing = _read("CONTRIBUTING.md")
    cli = _read("frontier_tooling/cli.py")
    powershell = _read("scripts/frontier.ps1")
    makefile = _read("Makefile")

    assert "make dev" not in readme
    assert "lattix dev" not in readme
    assert "local-up" in readme
    assert "make dev" not in deployment
    assert "docker-compose.local.yml" in deployment
    assert "make dev" not in contributing
    assert '@cli.command("dev")' not in cli
    assert '"local-up"' in cli
    assert '"local-down"' in cli
    assert '"remove"' in cli
    assert "docker-compose.local.yml" in powershell
    assert '"remove"' in powershell
    assert "local-up" in makefile
    assert "remove:" in makefile


def test_makefile_prefers_repo_venv_python_and_quotes_env_bootstrap_commands() -> None:
    makefile = _read("Makefile")

    assert "VENV_PYTHON := .venv/Scripts/python.exe" in makefile
    assert "VENV_PYTHON := .venv/bin/python" in makefile
    assert "CLI_RUNNER ?= $(PYTHON) -m frontier_tooling.cli" in makefile
    assert 'SECURE_ENV_FILE := $(strip $(shell "$(PYTHON)" -c "from frontier_tooling.common import ensure_compose_env_file; print(ensure_compose_env_file(local_profile=False))"))' in makefile
    assert 'LIGHTWEIGHT_ENV_FILE := $(strip $(shell "$(PYTHON)" -c "from frontier_tooling.common import ensure_compose_env_file; print(ensure_compose_env_file(local_profile=True))"))' in makefile
    assert "helm template lattix ./helm/lattix-frontier -f helm/lattix-frontier/values-prod.yaml > $(DEV_NULL)" in makefile


def test_makefile_routes_runtime_commands_through_shared_cli() -> None:
    makefile = _read("Makefile")

    assert "Canonical public install path: install/bootstrap.sh" in makefile
    assert "$(CLI_RUNNER) bootstrap" in makefile
    assert "$(CLI_RUNNER) up" in makefile
    assert "$(CLI_RUNNER) down" in makefile
    assert "$(CLI_RUNNER) remove" in makefile
    assert "$(CLI_RUNNER) local-up" in makefile
    assert "$(CLI_RUNNER) local-down" in makefile
    assert "$(CLI_RUNNER) stack-up" in makefile
    assert "$(CLI_RUNNER) stack-down" in makefile
    assert "$(CLI_RUNNER) health" in makefile
    assert "$(CLI_RUNNER) ps" in makefile
    assert "$(CLI_RUNNER) logs" in makefile
    assert "$(CLI_RUNNER) smoke" in makefile


def test_public_docs_expose_bootstrap_and_remove_flow() -> None:
    readme = _read("README.md")
    installer_docs = _read("docs/INSTALLER.md")
    deployment = _read("docs/DEPLOYMENT.md")

    assert "curl -fsSL https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/bootstrap.sh | sh" in readme
    assert "curl -fsSL https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/bootstrap.sh | sh" in installer_docs
    assert "curl -fsSL https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/bootstrap.sh | sh" in deployment
    assert "-UseBasicParsing" in readme
    assert "-UseBasicParsing" in installer_docs
    assert "-UseBasicParsing" in deployment
    assert "pwsh -File .\\install\\bootstrap.ps1" in readme
    assert "pwsh -File .\\install\\bootstrap.ps1" in installer_docs
    assert "pwsh -File .\\install\\bootstrap.ps1" in deployment
    assert "sh ./install/bootstrap.sh" in readme
    assert "sh ./install/bootstrap.sh" in installer_docs
    assert "sh ./install/bootstrap.sh" in deployment
    assert "raw.githubusercontent.com" in installer_docs
    assert "lattix remove" in readme
    assert "lattix remove" in installer_docs
    assert "lattix remove" in deployment


def test_bootstrap_powershell_script_avoids_powershell7_only_syntax() -> None:
    bootstrap_ps1 = _read("install/bootstrap.ps1")

    assert "??" not in bootstrap_ps1
    assert "$TempRoot = if ([string]::IsNullOrWhiteSpace($env:TEMP))" in bootstrap_ps1


def test_remove_installer_env_files_deletes_generated_envs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("frontier_tooling.common.INSTALLER_DIR", tmp_path / ".installer")
    monkeypatch.setattr(
        "frontier_tooling.common.SECURE_INSTALLER_ENV_PATH",
        tmp_path / ".installer" / "local-secure.env",
    )
    monkeypatch.setattr(
        "frontier_tooling.common.LIGHTWEIGHT_INSTALLER_ENV_PATH",
        tmp_path / ".installer" / "local-lightweight.env",
    )

    secure = tmp_path / ".installer" / "local-secure.env"
    lightweight = tmp_path / ".installer" / "local-lightweight.env"
    secure.parent.mkdir(parents=True, exist_ok=True)
    secure.write_text("A2A_JWT_SECRET=test\n", encoding="utf-8")
    lightweight.write_text("A2A_JWT_SECRET=test\n", encoding="utf-8")

    removed = remove_installer_env_files()

    assert removed == [secure, lightweight]
    assert not secure.exists()
    assert not lightweight.exists()