from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import os
import platform as platform_module


DEFAULT_SANDBOX_RUNNER_IMAGE = "python:3.12.10-slim-bookworm"


def sandbox_runner_image() -> str:
    return str(os.getenv("SANDBOX_RUNNER_IMAGE") or DEFAULT_SANDBOX_RUNNER_IMAGE).strip() or DEFAULT_SANDBOX_RUNNER_IMAGE


class HostPlatform(str, Enum):
    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"


class IsolationStrategy(str, Enum):
    LINUX_HARDENED_CONTAINER = "linux-hardened-container"
    MACOS_DOCKER = "macos-docker"
    WINDOWS_DOCKER = "windows-docker"


@dataclass(frozen=True)
class SandboxCapabilities:
    strict_syscalls: bool


@dataclass
class SandboxPolicy:
    platform: HostPlatform
    allow_network: bool = False
    allowed_hosts: list[str] = field(default_factory=list)
    allowed_read_paths: list[str] = field(default_factory=list)
    allowed_executables: list[str] = field(default_factory=list)
    strategy: IsolationStrategy = field(init=False)

    def __post_init__(self) -> None:
        strategy = {
            HostPlatform.LINUX: IsolationStrategy.LINUX_HARDENED_CONTAINER,
            HostPlatform.MACOS: IsolationStrategy.MACOS_DOCKER,
            HostPlatform.WINDOWS: IsolationStrategy.WINDOWS_DOCKER,
        }[self.platform]
        object.__setattr__(self, "strategy", strategy)

    def capabilities(self) -> SandboxCapabilities:
        return SandboxCapabilities(strict_syscalls=self.platform == HostPlatform.LINUX)


@dataclass
class ExecutionSpec:
    tool_id: str
    command: list[str]
    input_paths: list[str] = field(default_factory=list)
    output_paths: list[str] = field(default_factory=list)
    requested_hosts: list[str] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    backend: str
    docker_command: list[str]
    network_name: str | None = None


@dataclass
class ExecutionPlanResult:
    executed: bool
    plan: ExecutionPlan


class ToolJailService:
    async def plan(self, spec: ExecutionSpec, policy: SandboxPolicy) -> ExecutionPlanResult:
        executable = spec.command[0] if spec.command else spec.tool_id
        if policy.allowed_executables and executable not in policy.allowed_executables:
            raise PermissionError(f"Executable '{executable}' is not allowlisted")
        if spec.requested_hosts:
            requested = set(spec.requested_hosts)
            allowed = set(policy.allowed_hosts)
            if not requested.issubset(allowed):
                raise PermissionError("Requested hosts are not allowlisted")
        backend = {
            HostPlatform.LINUX: "docker-linux",
            HostPlatform.MACOS: "docker-macos",
            HostPlatform.WINDOWS: "docker-windows",
        }[policy.platform]
        network_name = "frontier-sandbox-internal" if policy.allow_network else None
        docker_command = [
            "docker",
            "run",
            "--rm",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
        ]
        if network_name:
            docker_command.append(f"--network={network_name}")
        docker_command.extend([sandbox_runner_image(), *spec.command])
        return ExecutionPlanResult(
            executed=False,
            plan=ExecutionPlan(backend=backend, docker_command=docker_command, network_name=network_name),
        )


def detect_host_platform(system_name: str | None = None) -> HostPlatform:
    normalized = str(system_name or platform_module.system()).strip().lower()
    if normalized == "darwin":
        return HostPlatform.MACOS
    if normalized == "windows":
        return HostPlatform.WINDOWS
    return HostPlatform.LINUX
