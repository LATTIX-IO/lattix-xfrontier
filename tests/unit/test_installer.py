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
        openai_api_key="",
        federation_enabled=True,
        federation_cluster_name="cluster-a",
        federation_region="us-east",
        federation_peers=["https://peer.example.com"],
    )
    env_path = installer._write_env_file(answers, {"A2A_JWT_SECRET": secrets.token_urlsafe(32)})
    text = env_path.read_text(encoding="utf-8")
    assert env_path == tmp_path / ".installer" / "local-secure.env"
    assert "LOCAL_STACK_HOST=demo.localhost" in text
    assert "FRONTIER_RUNTIME_PROFILE=local-secure" in text
    assert "NEXT_PUBLIC_API_BASE_URL=/api" in text
    assert "FRONTEND_ORIGIN=http://demo.localhost" in text
    assert "A2A_JWT_AUD=frontier-runtime" in text
    assert "FEDERATION_ENABLED=true" in text
    assert "A2A_JWT_SECRET=" in text


def test_installer_generates_local_secret_when_blank(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(installation_root=str(tmp_path), deployment_mode="local")
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    secrets_map = installer._collect_local_secrets(answers)

    assert secrets_map["A2A_JWT_SECRET"]
    assert len(secrets_map["A2A_JWT_SECRET"]) >= 32


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