"""Installer diagnostics for local and enterprise deployment readiness."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import socket
import subprocess


@dataclass(slots=True)
class DiagnosticResult:
    """Result of a single installer diagnostic check."""

    name: str
    ok: bool
    message: str


LOCALHOST_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")


def command_available(name: str) -> DiagnosticResult:
    """Check whether a command is available on PATH."""

    found = shutil.which(name) is not None
    return DiagnosticResult(name=f"command:{name}", ok=found, message="found" if found else "missing from PATH")


def docker_daemon_available() -> DiagnosticResult:
    """Check whether the Docker daemon is reachable."""

    if shutil.which("docker") is None:
        return DiagnosticResult(name="docker-daemon", ok=False, message="docker CLI not found")
    try:
        completed = subprocess.run(
            ["docker", "info", "--format", "{{json .ServerVersion}}"],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except OSError as exc:
        return DiagnosticResult(name="docker-daemon", ok=False, message=str(exc))
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        message = "docker CLI is installed but the Docker daemon is not reachable"
        if detail:
            message = f"{message}. Start Docker Desktop or the docker service, then rerun the installer. Details: {detail}"
        else:
            message = f"{message}. Start Docker Desktop or the docker service, then rerun the installer."
        return DiagnosticResult(name="docker-daemon", ok=False, message=message)
    return DiagnosticResult(name="docker-daemon", ok=True, message=completed.stdout.strip() or "docker daemon reachable")


def docker_compose_available() -> DiagnosticResult:
    """Check whether the Docker Compose v2 plugin is available."""

    if shutil.which("docker") is None:
        return DiagnosticResult(name="docker-compose-plugin", ok=False, message="docker CLI not found")
    try:
        completed = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except OSError as exc:
        return DiagnosticResult(name="docker-compose-plugin", ok=False, message=str(exc))
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "docker compose version failed"
        return DiagnosticResult(
            name="docker-compose-plugin",
            ok=False,
            message=f"Docker Compose v2 plugin is not available. Details: {detail}",
        )
    return DiagnosticResult(
        name="docker-compose-plugin",
        ok=True,
        message=completed.stdout.strip() or "docker compose available",
    )


def port_available(port: int) -> DiagnosticResult:
    """Check whether a local TCP port can be bound."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as exc:
            return DiagnosticResult(name=f"port:{port}", ok=False, message=str(exc))
    return DiagnosticResult(name=f"port:{port}", ok=True, message="available")


def hostname_prefix_valid(prefix: str) -> DiagnosticResult:
    """Validate that a localhost vanity prefix is safe to use."""

    valid = bool(LOCALHOST_NAME_RE.fullmatch(prefix))
    return DiagnosticResult(
        name="hostname-prefix",
        ok=valid,
        message="valid" if valid else "must be lowercase alphanumeric or hyphen and DNS-safe",
    )


def helm_available() -> DiagnosticResult:
    """Check whether Helm is available for enterprise deployments."""

    return command_available("helm")


def kubectl_available() -> DiagnosticResult:
    """Check whether kubectl is available for enterprise deployments."""

    return command_available("kubectl")


def writable_directory(path: Path) -> DiagnosticResult:
    """Check whether a directory exists or can be created and written to."""

    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".frontier-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        return DiagnosticResult(name=f"write:{path}", ok=False, message=str(exc))
    return DiagnosticResult(name=f"write:{path}", ok=True, message="writable")
