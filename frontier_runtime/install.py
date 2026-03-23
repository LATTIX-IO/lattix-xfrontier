from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import getpass
import re
import secrets
import shutil
import socket
import subprocess
from typing import Iterable


@dataclass(frozen=True)
class DiagnosticResult:
    name: str
    ok: bool
    message: str


def hostname_prefix_valid(prefix: str) -> DiagnosticResult:
    normalized = str(prefix).strip()
    ok = bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", normalized))
    return DiagnosticResult("hostname-prefix", ok, "valid" if ok else "Use lowercase letters, numbers, and hyphens only")


def writable_directory(path: Path) -> DiagnosticResult:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        return DiagnosticResult("writable-directory", False, str(exc))
    return DiagnosticResult("writable-directory", True, "writable")


def port_available(port: int) -> DiagnosticResult:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with sock:
            sock.bind(("127.0.0.1", port))
    except OSError as exc:
        return DiagnosticResult(f"port:{port}", False, str(exc))
    return DiagnosticResult(f"port:{port}", True, "available")


def docker_daemon_available() -> DiagnosticResult:
    if shutil.which("docker") is None:
        return DiagnosticResult("docker-daemon", False, "Docker is not installed or not on PATH")
    result = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if result.returncode != 0:
        return DiagnosticResult("docker-daemon", False, "Start Docker Desktop or the docker service before continuing")
    return DiagnosticResult("docker-daemon", True, "available")


def docker_compose_available() -> DiagnosticResult:
    if shutil.which("docker") is None:
        return DiagnosticResult("docker-compose", False, "Docker is not installed or not on PATH")
    result = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True)
    if result.returncode != 0:
        return DiagnosticResult("docker-compose", False, "Docker Compose v2 plugin is not available")
    return DiagnosticResult("docker-compose", True, "available")


@dataclass(frozen=True)
class PrerequisiteDefinition:
    key: str
    display_name: str
    check_name: str
    install_commands: tuple[tuple[str, ...], ...] = ()
    manual_steps: tuple[str, ...] = ()


@dataclass(frozen=True)
class MissingPrerequisite:
    definition: PrerequisiteDefinition
    result: DiagnosticResult


@dataclass
class InstallerAnswers:
    installation_root: str
    deployment_mode: str = "local"
    local_hostname: str = "frontier"
    openai_api_key: str = ""
    federation_enabled: bool = False
    federation_cluster_name: str = ""
    federation_region: str = ""
    federation_peers: list[str] = field(default_factory=list)


class FrontierInstaller:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    def _write_env_file(self, answers: InstallerAnswers, secrets_map: dict[str, str]) -> Path:
        generated_dir = self.repo_root / ".installer"
        generated_dir.mkdir(parents=True, exist_ok=True)
        env_path = generated_dir / "local.env"
        base_lines: list[str] = []
        example_path = self.repo_root / ".env.example"
        if example_path.exists():
            base_lines = [line.rstrip("\n") for line in example_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        generated_lines = [
            *base_lines,
            f"LOCAL_STACK_HOST={answers.local_hostname}.localhost",
            "NEXT_PUBLIC_API_BASE_URL=/api",
            f"FEDERATION_ENABLED={'true' if answers.federation_enabled else 'false'}",
            f"FEDERATION_CLUSTER_NAME={answers.federation_cluster_name}",
            f"FEDERATION_REGION={answers.federation_region}",
            f"FEDERATION_PEERS={','.join(answers.federation_peers)}",
        ]
        for key, value in secrets_map.items():
            generated_lines.append(f"{key}={value}")
        env_path.write_text("\n".join(generated_lines) + "\n", encoding="utf-8")
        return env_path

    def _collect_local_secrets(self, answers: InstallerAnswers) -> dict[str, str]:
        if answers.deployment_mode == "enterprise":
            return {}
        provided = getpass.getpass("A2A_JWT_SECRET (leave blank to generate): ").strip()
        return {"A2A_JWT_SECRET": provided or secrets.token_urlsafe(32)}

    def _write_generated_helm_values(self, answers: InstallerAnswers) -> Path:
        output = self.repo_root / ".installer" / "generated-values.yaml"
        output.parent.mkdir(parents=True, exist_ok=True)
        peer_lines = "\n".join(f"  - {peer}" for peer in answers.federation_peers)
        output.write_text(
            "\n".join(
                [
                    f"clusterName: {answers.federation_cluster_name}",
                    f"region: {answers.federation_region}",
                    "peers:",
                    peer_lines or "  []",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return output

    def _ask_yes_no(self, prompt: str, default: bool) -> bool:
        return default

    def _run_install_command(self, command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, capture_output=True, text=True)

    def _run_prerequisite_check(self, definition: PrerequisiteDefinition) -> DiagnosticResult:
        return DiagnosticResult(definition.check_name, True, "available")

    def _attempt_missing_prerequisite_installs(
        self,
        missing: Iterable[MissingPrerequisite],
    ) -> list[MissingPrerequisite]:
        unresolved: list[MissingPrerequisite] = []
        for item in missing:
            install_succeeded = False
            failure_message = item.result.message
            for command in item.definition.install_commands:
                result = self._run_install_command(command)
                if result.returncode == 0:
                    install_succeeded = True
                    break
                failure_message = result.stderr or result.stdout or failure_message
            if not install_succeeded:
                unresolved.append(
                    MissingPrerequisite(
                        definition=item.definition,
                        result=DiagnosticResult(item.definition.check_name, False, failure_message),
                    )
                )
        return unresolved

    def _resolve_missing_prerequisites(self, missing: list[MissingPrerequisite], intro: str) -> None:
        if not missing:
            return
        if self._ask_yes_no(intro, True):
            unresolved = self._attempt_missing_prerequisite_installs(missing)
            if not unresolved:
                return
            missing = unresolved
        lines = ["Outstanding prerequisites:"]
        for item in missing:
            lines.append(f"- {item.definition.display_name}: {item.result.message}")
            for command in item.definition.install_commands:
                lines.append("  " + " ".join(command))
            for step in item.definition.manual_steps:
                lines.append("  " + step)
        raise SystemExit("\n".join(lines))
