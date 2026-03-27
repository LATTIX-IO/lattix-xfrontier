from pathlib import Path

from frontier_tooling.common import ensure_compose_env_file, remove_installer_artifacts, remove_installer_env_files


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
    assert "Install OPA" in ci
    assert "opa_linux_amd64_static" in ci
    assert "python scripts/run_opa.py test policies/ -v" in ci
    assert "helm lint ./helm/lattix-frontier" in ci
    assert "helm template lattix ./helm/lattix-frontier -f helm/lattix-frontier/values-prod.yaml > /dev/null" in ci
    assert "helm-validate:" in makefile
    assert 'function Get-HelmCommand' in powershell
    assert '.tools\\helm\\windows-amd64\\helm.exe' in powershell
    assert 'Get-Command helm.exe' in powershell
    assert '"helm-validate"' in powershell


def test_compose_files_avoid_global_container_and_network_names() -> None:
    secure_compose = _read("docker-compose.yml")
    local_compose = _read("docker-compose.local.yml")

    assert "container_name:" not in secure_compose
    assert "container_name:" not in local_compose
    assert "name: frontier-sandbox-internal" not in secure_compose


def test_bootstrap_installer_reports_secure_compose_env_path() -> None:
    installer = _read("frontier_tooling/installer.py")
    installer_docs = _read("docs/INSTALLER.md")

    assert 'ensure_compose_env_file(local_profile=False, root=install_root)' in installer
    assert 'FrontierInstaller(repo_root=install_root)' in installer
    assert 'collect_local_answers(installation_root=install_root' in installer
    assert 'installer._write_env_file(answers, secrets_map)' in installer
    assert '"compose_env": str(compose_env.resolve())' in installer
    assert 'def _print_install_result' in installer
    assert 'def _render_install_summary' in installer
    assert ".installer/local-secure.env" in installer_docs
    assert ".installer/local-lightweight.env" not in installer_docs


def test_compose_env_generation_uses_mode_specific_files_and_profiles(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("A2A_JWT_AUD=frontier-runtime\n", encoding="utf-8")

    secure_env = ensure_compose_env_file(local_profile=False, root=tmp_path)
    lightweight_env = ensure_compose_env_file(local_profile=True, root=tmp_path)

    assert secure_env.name == "local-secure.env"
    assert lightweight_env.name == "local-lightweight.env"

    secure_text = secure_env.read_text(encoding="utf-8")
    lightweight_text = lightweight_env.read_text(encoding="utf-8")

    assert "FRONTIER_RUNTIME_PROFILE=local-secure" in secure_text
    assert "NEXT_PUBLIC_API_BASE_URL=/api" in secure_text
    assert "A2A_JWT_AUD=frontier-runtime" in secure_text
    assert "LOCAL_STACK_HOST=xfrontier.local" in secure_text
    assert "FRONTEND_ORIGIN=http://xfrontier.local" in secure_text
    assert "FRONTIER_LOCAL_BOOTSTRAP_AUTHENTICATED_OPERATOR=true" in secure_text
    assert "FRONTIER_LOCAL_API_BASE_URL=http://127.0.0.1/api" in secure_text

    assert "FRONTIER_RUNTIME_PROFILE=local-lightweight" in lightweight_text
    assert "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" in lightweight_text
    assert "A2A_JWT_AUD=frontier-runtime" in lightweight_text
    assert "LOCAL_STACK_HOST=xfrontier.local" in lightweight_text
    assert "FRONTIER_LOCAL_API_BASE_URL=http://localhost:8000" in lightweight_text


def test_compose_env_generation_respects_non_default_gateway_port(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("LOCAL_GATEWAY_HTTP_PORT=8080\n", encoding="utf-8")

    secure_env = ensure_compose_env_file(local_profile=False, root=tmp_path)
    secure_text = secure_env.read_text(encoding="utf-8")

    assert "LOCAL_GATEWAY_HTTP_PORT=8080" in secure_text
    assert "FRONTEND_ORIGIN=http://xfrontier.local:8080" in secure_text
    assert "FRONTIER_LOCAL_API_BASE_URL=http://127.0.0.1:8080/api" in secure_text


def test_compose_env_generation_repairs_blank_a2a_secret(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".env").write_text("A2A_JWT_SECRET=from-dot-env\n", encoding="utf-8")
    (tmp_path / ".installer").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".installer" / "local-secure.env").write_text("A2A_JWT_SECRET=\n", encoding="utf-8")

    secure_env = ensure_compose_env_file(local_profile=False, root=tmp_path)
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
    assert '@cli.command("update")' in cli
    assert '"local-up"' in cli
    assert '"local-down"' in cli
    assert '"remove"' in cli
    assert '"update"' in powershell
    assert "docker-compose.local.yml" in powershell
    assert '"remove"' in powershell
    assert "local-up" in makefile
    assert "remove:" in makefile
    assert "update:" in makefile


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
    assert "$(CLI_RUNNER) update" in makefile
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
    docs = (readme, installer_docs, deployment)

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
    assert "lattix remove" in readme
    assert "lattix remove" in installer_docs
    assert "lattix remove" in deployment
    assert "lattix update" in readme
    assert "lattix update" in installer_docs
    for doc in docs:
        assert "xfrontier.local" in doc
        assert "LOCAL_STACK_HOST" in doc


def test_bootstrap_powershell_script_avoids_powershell7_only_syntax() -> None:
    bootstrap_ps1 = _read("install/bootstrap.ps1")

    assert "??" not in bootstrap_ps1
    assert "$TempRoot = if ([string]::IsNullOrWhiteSpace($env:TEMP))" in bootstrap_ps1


def test_bootstrap_powershell_script_validates_python_runtime() -> None:
    bootstrap_ps1 = _read("install/bootstrap.ps1")
    installer_docs = _read("docs/INSTALLER.md")
    readme = _read("README.md")

    assert "function Test-PythonCommand" in bootstrap_ps1
    assert "function Stop-Bootstrap" in bootstrap_ps1
    assert "$commandExitCode = $LASTEXITCODE" in bootstrap_ps1
    assert "$installerExitCode = $LASTEXITCODE" in bootstrap_ps1
    assert "Stop-Bootstrap -Message \"Installer failed with exit code $installerExitCode." in bootstrap_ps1
    assert "exit $installerExitCode" not in bootstrap_ps1
    assert "working 'py' or 'python' command" in bootstrap_ps1
    assert "App execution aliases" in bootstrap_ps1
    assert "working Python 3 runtime" in installer_docs
    assert "working Python 3 runtime" in readme


def test_bootstrap_shell_script_does_not_replace_caller_shell() -> None:
    bootstrap_sh = _read("install/bootstrap.sh")

    assert 'exec "$PYTHON_BIN" "$BOOTSTRAP_DIR/frontier-installer.py"' not in bootstrap_sh
    assert 'Installer failed with exit code $installer_exit_code. The current shell was left intact' in bootstrap_sh


def test_public_frontier_installer_imports_packaged_module() -> None:
    public_installer = _read("install/frontier-installer.py")
    bootstrap_ps1 = _read("install/bootstrap.ps1")
    bootstrap_sh = _read("install/bootstrap.sh")
    tooling_common = _read("frontier_tooling/common.py")
    packaged_installer = _read("frontier_tooling/installer.py")
    manifest = _read("install/manifest.json")

    assert 'import importlib' in public_installer
    assert 'import sys' in public_installer
    assert 'importlib.import_module("frontier_tooling.installer")' in public_installer
    assert 'module.main()' in public_installer
    assert 'runpy.run_path' not in public_installer
    assert 'urlopen(' not in public_installer
    assert '_validated_archive_url' in public_installer
    assert 'http.client.HTTPSConnection' in public_installer
    assert 'FRONTIER_ARCHIVE_URL' not in public_installer
    assert 'cwd = Path.cwd()' not in public_installer
    assert 'if packaged.exists():' not in public_installer
    assert '$env:INSTALLER_URL' not in bootstrap_ps1
    assert '${INSTALLER_URL:-' not in bootstrap_sh
    assert 'import httpx' not in tooling_common.split('def request_json', 1)[0]
    assert 'import sysconfig' in tooling_common
    assert 'sysconfig.get_preferred_scheme("user")' in tooling_common
    assert 'sysconfig.get_path("scripts", scheme=scheme)' in tooling_common
    assert 'def request_json' in tooling_common
    assert '    import httpx' in tooling_common
    assert 'httpx.request(' in tooling_common
    assert '_validated_http_url' in tooling_common
    assert 'return "editable" if (root / ".git").exists() else "wheel"' in packaged_installer
    assert 'if _install_mode(root) == "editable":' in packaged_installer
    assert 'args.append("--user")' in packaged_installer
    assert 'args.append("-e")' in packaged_installer
    assert 'args.append(".[dev]")' in packaged_installer
    assert '"install_mode": mode' in packaged_installer
    assert '"auto_started": True' in packaged_installer
    assert '"urls": urls' in packaged_installer
    assert 'FRONTIER_INSTALLER_OUTPUT' in packaged_installer
    assert 'return "tui" if sys.stdout.isatty() else "json"' in packaged_installer
    assert 'print_json(payload)' in packaged_installer
    assert 'Lattix xFrontier install complete' in packaged_installer
    assert 'Secure local profile (single-host compose, authenticated A2A)' in packaged_installer
    assert 'Use the hosted or enterprise deployment path when you need per-agent workload isolation' in packaged_installer
    assert 'Install src :' in packaged_installer
    assert 'def update() -> None:' in packaged_installer
    assert 'lattix update' in manifest
    assert '"version": "0.1.0"' in manifest
    assert 'DEFAULT_LOCAL_STACK_HOST = "xfrontier.local"' in tooling_common


def test_remove_installer_env_files_deletes_generated_envs(tmp_path: Path, monkeypatch) -> None:
    secure = tmp_path / ".installer" / "local-secure.env"
    lightweight = tmp_path / ".installer" / "local-lightweight.env"
    secure.parent.mkdir(parents=True, exist_ok=True)
    secure.write_text("A2A_JWT_SECRET=test\n", encoding="utf-8")
    lightweight.write_text("A2A_JWT_SECRET=test\n", encoding="utf-8")

    removed = remove_installer_env_files(root=tmp_path)

    assert removed == [secure, lightweight]
    assert not secure.exists()
    assert not lightweight.exists()


def test_remove_installer_artifacts_deletes_legacy_and_generated_files(tmp_path: Path) -> None:
    installer_root = tmp_path / ".installer"
    secure = installer_root / "local-secure.env"
    lightweight = installer_root / "local-lightweight.env"
    legacy = installer_root / "local.env"
    generated_values = installer_root / "generated-values.yaml"
    installer_root.mkdir(parents=True, exist_ok=True)
    secure.write_text("A2A_JWT_SECRET=test\n", encoding="utf-8")
    lightweight.write_text("A2A_JWT_SECRET=test\n", encoding="utf-8")
    legacy.write_text("A2A_JWT_SECRET=legacy\n", encoding="utf-8")
    generated_values.write_text("clusterName: demo\n", encoding="utf-8")

    removed = remove_installer_artifacts(root=tmp_path)

    assert removed == [secure, lightweight, legacy, generated_values]
    assert not installer_root.exists()

def test_remove_command_tracks_failed_teardowns_and_radius_secret_is_not_hardcoded() -> None:
    cli = _read("frontier_tooling/cli.py")
    tooling = _read("frontier_tooling/common.py")
    powershell = _read("scripts/frontier.ps1")
    casdoor = _read("docker/casdoor/start-casdoor.sh")
    compose = _read("docker-compose.yml")
    gitattributes = _read(".gitattributes")

    assert '"failed_teardowns": failed_teardowns' in cli
    assert '"deleted_artifacts": [str(path) for path in removed_artifacts]' in cli
    assert '"removed": removed' in cli
    assert 'def _request_local_api' in cli
    assert 'configured_local_api_url(path)' in cli
    assert 'def configured_local_api_base_url' in tooling
    assert 'def configured_local_api_headers' in tooling
    assert 'extra_headers=configured_local_api_headers()' in cli
    assert 'FRONTIER_LOCAL_API_BASE_URL=http://127.0.0.1/api' in _read(".env.example")
    assert 'function Get-ConfiguredApiBaseUrl' in powershell
    assert 'function Get-ConfiguredApiHostHeader' in powershell
    assert 'http://localhost:8000' not in powershell.split('function Show-Help', 1)[1].split('"local-up"', 1)[0]
    assert 'CASDOOR_RADIUS_SECRET="${CASDOOR_RADIUS_SECRET:-${POSTGRES_PASSWORD}}"' in casdoor
    assert 'radiusSecret = "${CASDOOR_RADIUS_SECRET}"' in casdoor
    assert 'radiusSecret = "secret"' not in casdoor
    assert "tr -d '\\\\r' < /docker/casdoor/start-casdoor.sh > /tmp/start-casdoor.sh" in compose
    assert "docker/casdoor/start-casdoor.sh text eol=lf" in gitattributes
    assert "*.sh text eol=lf" in gitattributes

def test_precommit_script_runs_repo_native_checks() -> None:
    precommit = _read("precommit.ps1")

    assert 'Write-Host "Lattix xFrontier pre-commit checks"' in precommit
    assert 'function Invoke-Python' in precommit
    assert 'function Write-StepSummary' in precommit
    assert 'Invoke-Step -Name "Install Python dependencies"' in precommit
    assert 'Invoke-Step -Name "Install frontend dependencies"' in precommit
    assert 'Invoke-Step -Name "Python lint"' in precommit
    assert 'Invoke-Step -Name "Python typecheck"' in precommit
    assert 'Invoke-Step -Name "Python tests"' in precommit
    assert 'Invoke-Step -Name "Policy tests"' in precommit
    assert 'Invoke-Step -Name "Frontend lint"' in precommit
    assert 'Invoke-Step -Name "Frontend tests"' in precommit
    assert 'Invoke-Step -Name "Frontend build"' in precommit
    assert 'Invoke-IfAvailable -CommandName "semgrep"' in precommit
    assert 'Invoke-IfAvailable -CommandName "gitleaks"' in precommit
    assert 'Invoke-IfAvailable -CommandName "trivy"' in precommit
    assert 'function Get-HelmCommand' in precommit
    assert '.tools\\helm\\windows-amd64\\helm.exe' in precommit
    assert 'Get-Command helm.exe' in precommit
    assert 'Invoke-Step -Name "Helm chart validation"' in precommit
    assert 'missing helm.exe' in precommit
    assert 'Write-StepSummary -Final' in precommit
