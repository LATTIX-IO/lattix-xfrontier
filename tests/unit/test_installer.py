from pathlib import Path
import secrets
import subprocess

import pytest

from frontier_runtime.install import DiagnosticResult, FrontierInstaller, InstallerAnswers, MissingPrerequisite, PrerequisiteDefinition


def test_installer_writes_env_file(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("LOG_LEVEL=INFO\n", encoding="utf-8")
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        local_hostname="demo",
        oidc_provider_template="casdoor",
        oidc_issuer="http://casdoor.demo.localhost",
        oidc_audience="frontier-ui",
        oidc_jwks_url="http://casdoor.demo.localhost/.well-known/jwks.json",
        oidc_client_id="frontier-web",
        oidc_authorization_url="http://casdoor.demo.localhost/login/oauth/authorize",
        oidc_token_url="http://casdoor.demo.localhost/api/login/oauth/access_token",
        openai_api_key="",
        federation_enabled=True,
        federation_cluster_name="cluster-a",
        federation_region="us-east",
        federation_peers=["https://peer.example.com"],
    )
    env_path = installer._write_env_file(
        answers,
        {
            "A2A_JWT_SECRET": secrets.token_urlsafe(32),
            "POSTGRES_PASSWORD": "db-secret",
            "NEO4J_PASSWORD": "neo-secret",
        },
    )
    text = env_path.read_text(encoding="utf-8")
    assert env_path == tmp_path / ".installer" / "local-secure.env"
    assert "LOCAL_STACK_HOST=demo.localhost" in text
    assert "FRONTIER_RUNTIME_PROFILE=local-secure" in text
    assert "NEXT_PUBLIC_API_BASE_URL=/api" in text
    assert "FRONTEND_ORIGIN=http://demo.localhost" in text
    assert "FRONTIER_REQUIRE_AUTHENTICATED_REQUESTS=true" in text
    assert "FRONTIER_ALLOW_HEADER_ACTOR_AUTH=false" in text
    assert "FRONTIER_AUTH_MODE=oidc" in text
    assert "CASDOOR_LOCAL_HOST=casdoor.localhost" in text
    assert "CASDOOR_PUBLIC_URL=http://casdoor.localhost" in text
    assert "FRONTIER_BOOTSTRAP_ADMIN_USERNAME=frontier-admin" in text
    assert "FRONTIER_BOOTSTRAP_ADMIN_EMAIL=admin@demo.localhost" in text
    assert "FRONTIER_BOOTSTRAP_ADMIN_SUBJECT=frontier-admin" in text
    assert "FRONTIER_ADMIN_ACTORS=frontier-admin,admin@demo.localhost" in text
    assert "FRONTIER_BUILDER_ACTORS=frontier-admin,admin@demo.localhost" in text
    assert "FRONTIER_API_BEARER_TOKEN=" in text
    assert "FRONTIER_AUTH_OIDC_PROVIDER=casdoor" in text
    assert "FRONTIER_AUTH_OIDC_ISSUER=http://casdoor.demo.localhost" in text
    assert "FRONTIER_AUTH_OIDC_AUDIENCE=frontier-ui" in text
    assert "FRONTIER_AUTH_OIDC_JWKS_URL=http://casdoor.demo.localhost/.well-known/jwks.json" in text
    assert "FRONTIER_AUTH_OIDC_CLIENT_ID=frontier-web" in text
    assert "FRONTIER_AUTH_OIDC_AUTHORIZATION_URL=http://casdoor.demo.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_TOKEN_URL=http://casdoor.demo.localhost/api/login/oauth/access_token" in text
    assert "FRONTIER_AUTH_OIDC_SIGNIN_URL=http://casdoor.demo.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_SIGNUP_URL=http://casdoor.demo.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_SCOPES=openid profile email" in text
    assert "A2A_JWT_AUD=frontier-runtime" in text
    assert "FEDERATION_ENABLED=true" in text
    assert "A2A_JWT_SECRET=" in text
    assert "POSTGRES_PASSWORD=db-secret" in text
    assert "NEO4J_PASSWORD=neo-secret" in text


def test_installer_generates_local_secret_when_blank(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(installation_root=str(tmp_path), deployment_mode="local")
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    secrets_map = installer._collect_local_secrets(answers)

    assert secrets_map["A2A_JWT_SECRET"]
    assert len(secrets_map["A2A_JWT_SECRET"]) >= 32
    assert secrets_map["POSTGRES_PASSWORD"]
    assert secrets_map["NEO4J_PASSWORD"]
    assert "FRONTIER_API_BEARER_TOKEN" not in secrets_map


def test_installer_defaults_to_casdoor_oidc_preset(tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(installation_root=str(tmp_path), deployment_mode="local")

    env_path = installer._write_env_file(
        answers,
        {
            "A2A_JWT_SECRET": secrets.token_urlsafe(32),
            "POSTGRES_PASSWORD": "db-secret",
            "NEO4J_PASSWORD": "neo-secret",
        },
    )
    text = env_path.read_text(encoding="utf-8")

    assert "FRONTIER_AUTH_MODE=oidc" in text
    assert "FRONTIER_AUTH_OIDC_PROVIDER=casdoor" in text
    assert "FRONTIER_AUTH_OIDC_ISSUER=http://casdoor.localhost" in text
    assert "FRONTIER_AUTH_OIDC_AUDIENCE=frontier-ui" in text
    assert "FRONTIER_AUTH_OIDC_JWKS_URL=http://casdoor.localhost/.well-known/jwks.json" in text
    assert "FRONTIER_AUTH_OIDC_CLIENT_ID=frontier-web" in text
    assert "FRONTIER_AUTH_OIDC_AUTHORIZATION_URL=http://casdoor.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_TOKEN_URL=http://casdoor.localhost/api/login/oauth/access_token" in text


def test_installer_writes_casdoor_preset_when_selected(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        deployment_mode="local",
        local_auth_provider="oidc",
        oidc_provider_template="casdoor",
        oidc_issuer="http://casdoor.localhost",
        oidc_audience="frontier-ui",
        oidc_jwks_url="http://casdoor.localhost/.well-known/jwks.json",
        oidc_client_id="frontier-web",
        oidc_authorization_url="http://casdoor.localhost/login/oauth/authorize",
        oidc_token_url="http://casdoor.localhost/api/login/oauth/access_token",
    )
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    secrets_map = installer._collect_local_secrets(answers)
    env_path = installer._write_env_file(answers, secrets_map)
    text = env_path.read_text(encoding="utf-8")

    assert "FRONTIER_API_BEARER_TOKEN=" in text
    assert "FRONTIER_AUTH_MODE=oidc" in text
    assert "FRONTIER_AUTH_OIDC_PROVIDER=casdoor" in text
    assert "FRONTIER_AUTH_OIDC_ISSUER=http://casdoor.localhost" in text
    assert "FRONTIER_AUTH_OIDC_AUDIENCE=frontier-ui" in text
    assert "FRONTIER_AUTH_OIDC_JWKS_URL=http://casdoor.localhost/.well-known/jwks.json" in text
    assert "FRONTIER_AUTH_OIDC_CLIENT_ID=frontier-web" in text
    assert "FRONTIER_AUTH_OIDC_AUTHORIZATION_URL=http://casdoor.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_TOKEN_URL=http://casdoor.localhost/api/login/oauth/access_token" in text
    assert "FRONTIER_AUTH_OIDC_SIGNIN_URL=http://casdoor.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_SIGNUP_URL=http://casdoor.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_SCOPES=openid profile email" in text
    assert "FRONTIER_API_BEARER_TOKEN" not in secrets_map


def test_installer_treats_legacy_casdoor_mode_as_oidc(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        deployment_mode="local",
        local_auth_provider="casdoor",
    )
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    secrets_map = installer._collect_local_secrets(answers)
    env_path = installer._write_env_file(answers, secrets_map)
    text = env_path.read_text(encoding="utf-8")

    assert "FRONTIER_AUTH_MODE=oidc" in text
    assert "FRONTIER_AUTH_OIDC_PROVIDER=casdoor" in text
    assert "FRONTIER_AUTH_OIDC_SIGNIN_URL=http://casdoor.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_SIGNUP_URL=http://casdoor.localhost/login/oauth/authorize" in text
    assert "FRONTIER_API_BEARER_TOKEN" not in secrets_map


def test_installer_supports_external_oidc_provider(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        deployment_mode="local",
        local_auth_provider="oidc",
        oidc_provider_template="external",
        oidc_issuer="https://login.example.com/realms/frontier",
        oidc_audience="frontier-api",
        oidc_jwks_url="https://login.example.com/realms/frontier/protocol/openid-connect/certs",
        oidc_client_id="frontier-ui",
        oidc_authorization_url="https://login.example.com/realms/frontier/protocol/openid-connect/auth",
        oidc_token_url="https://login.example.com/realms/frontier/protocol/openid-connect/token",
        oidc_signin_url="https://login.example.com/realms/frontier/protocol/openid-connect/auth?prompt=login",
        oidc_signup_url="https://login.example.com/realms/frontier/registrations/start",
        oidc_scopes=["openid", "profile", "email", "groups"],
    )
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    secrets_map = installer._collect_local_secrets(answers)
    env_path = installer._write_env_file(answers, secrets_map)
    text = env_path.read_text(encoding="utf-8")

    assert "FRONTIER_AUTH_MODE=oidc" in text
    assert "FRONTIER_AUTH_OIDC_PROVIDER=oidc" in text
    assert "FRONTIER_AUTH_OIDC_ISSUER=https://login.example.com/realms/frontier" in text
    assert "FRONTIER_AUTH_OIDC_AUDIENCE=frontier-api" in text
    assert "FRONTIER_AUTH_OIDC_CLIENT_ID=frontier-ui" in text
    assert "FRONTIER_AUTH_OIDC_SIGNIN_URL=https://login.example.com/realms/frontier/protocol/openid-connect/auth?prompt=login" in text
    assert "FRONTIER_AUTH_OIDC_SIGNUP_URL=https://login.example.com/realms/frontier/registrations/start" in text
    assert "FRONTIER_AUTH_OIDC_SCOPES=openid profile email groups" in text
    assert "FRONTIER_API_BEARER_TOKEN" not in secrets_map


def test_installer_shared_token_mode_still_generates_bearer_secret(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        deployment_mode="local",
        local_auth_provider="shared-token",
    )
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    secrets_map = installer._collect_local_secrets(answers)
    env_path = installer._write_env_file(answers, secrets_map)
    text = env_path.read_text(encoding="utf-8")

    assert secrets_map["FRONTIER_API_BEARER_TOKEN"]
    assert "FRONTIER_AUTH_MODE=shared-token" in text
    assert "FRONTIER_API_BEARER_TOKEN=" in text
    assert "FRONTIER_AUTH_OIDC_PROVIDER=" in text


def test_installer_does_not_collect_local_secret_for_enterprise_only(tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(installation_root=str(tmp_path), deployment_mode="enterprise")

    secrets_map = installer._collect_local_secrets(answers)

    assert secrets_map == {}


def test_installer_writes_helm_values(tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        deployment_mode="enterprise",
        federation_enabled=True,
        federation_cluster_name="cluster-a",
        federation_region="us-west",
        federation_peers=["https://peer-a.example.com", "https://peer-b.example.com"],
    )
    values_path = installer._write_generated_helm_values(answers)
    text = values_path.read_text(encoding="utf-8")
    assert "clusterName: cluster-a" in text
    assert "https://peer-a.example.com" in text


def test_resolve_missing_prerequisites_attempts_install_and_continues(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    definition = PrerequisiteDefinition(
        key="helm",
        display_name="Helm",
        check_name="command:helm",
        install_commands=(("winget", "install", "Helm.Helm"),),
        manual_steps=("Install Helm manually.",),
    )
    missing = [
        MissingPrerequisite(
            definition=definition,
            result=DiagnosticResult(name="command:helm", ok=False, message="missing from PATH"),
        )
    ]

    monkeypatch.setattr(installer, "_ask_yes_no", lambda prompt, default: True)
    monkeypatch.setattr(
        installer,
        "_run_install_command",
        lambda command: subprocess.CompletedProcess(command, 0, stdout="installed", stderr=""),
    )
    monkeypatch.setattr(
        installer,
        "_run_prerequisite_check",
        lambda definition: DiagnosticResult(name=definition.check_name, ok=True, message="found"),
    )

    installer._resolve_missing_prerequisites(missing, intro="Need Helm")


def test_resolve_missing_prerequisites_decline_exits_with_actionable_message(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    definition = PrerequisiteDefinition(
        key="kubectl",
        display_name="kubectl",
        check_name="command:kubectl",
        install_commands=(("winget", "install", "Kubernetes.kubectl"),),
        manual_steps=("Install kubectl manually.",),
    )
    missing = [
        MissingPrerequisite(
            definition=definition,
            result=DiagnosticResult(name="command:kubectl", ok=False, message="missing from PATH"),
        )
    ]

    monkeypatch.setattr(installer, "_ask_yes_no", lambda prompt, default: False)

    with pytest.raises(SystemExit) as excinfo:
        installer._resolve_missing_prerequisites(missing, intro="Need kubectl")

    message = str(excinfo.value)
    assert "Outstanding prerequisites" in message
    assert "kubectl" in message
    assert "winget install Kubernetes.kubectl" in message


def test_attempt_missing_prerequisites_reports_failed_install(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    definition = PrerequisiteDefinition(
        key="docker",
        display_name="Docker",
        check_name="command:docker",
        install_commands=(("winget", "install", "Docker.DockerDesktop"),),
        manual_steps=("Install Docker manually.",),
    )
    missing = [
        MissingPrerequisite(
            definition=definition,
            result=DiagnosticResult(name="command:docker", ok=False, message="missing from PATH"),
        )
    ]

    monkeypatch.setattr(
        installer,
        "_run_install_command",
        lambda command: subprocess.CompletedProcess(command, 1, stdout="", stderr="installer failed"),
    )

    unresolved = installer._attempt_missing_prerequisite_installs(missing)

    assert len(unresolved) == 1
    assert unresolved[0].result.message == "installer failed"


def test_installer_yes_no_accepts_default_and_explicit_answers(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = iter(["", "n", "yes"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    assert installer._ask_yes_no("Proceed?", True) is True
    assert installer._ask_yes_no("Proceed?", True) is False
    assert installer._ask_yes_no("Proceed?", False) is True


def test_installer_yes_no_reprompts_on_invalid_input(monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = iter(["maybe", "Y"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    assert installer._ask_yes_no("Proceed?", False) is True
    captured = capsys.readouterr()
    assert "Please answer yes or no." in captured.out


def test_run_prerequisite_check_validates_named_commands(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    definition = PrerequisiteDefinition(
        key="helm",
        display_name="Helm",
        check_name="command:helm",
    )
    monkeypatch.setattr("shutil.which", lambda command: "C:/Tools/helm.exe" if command == "helm" else None)

    result = installer._run_prerequisite_check(definition)

    assert result.ok is True
    assert result.name == "command:helm"


def test_run_prerequisite_check_reports_missing_commands(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    definition = PrerequisiteDefinition(
        key="kubectl",
        display_name="kubectl",
        check_name="command:kubectl",
    )
    monkeypatch.setattr("shutil.which", lambda command: None)

    result = installer._run_prerequisite_check(definition)

    assert result.ok is False
    assert "kubectl is missing from PATH" == result.message


def test_attempt_missing_prerequisites_rechecks_after_install(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    definition = PrerequisiteDefinition(
        key="helm",
        display_name="Helm",
        check_name="command:helm",
        install_commands=(("winget", "install", "Helm.Helm"),),
    )
    missing = [
        MissingPrerequisite(
            definition=definition,
            result=DiagnosticResult(name="command:helm", ok=False, message="missing from PATH"),
        )
    ]
    monkeypatch.setattr(
        installer,
        "_run_install_command",
        lambda command: subprocess.CompletedProcess(command, 0, stdout="installed", stderr=""),
    )
    monkeypatch.setattr(
        installer,
        "_run_prerequisite_check",
        lambda definition: DiagnosticResult(name=definition.check_name, ok=False, message="still missing after install"),
    )

    unresolved = installer._attempt_missing_prerequisite_installs(missing)

    assert len(unresolved) == 1
    assert unresolved[0].result.message == "still missing after install"