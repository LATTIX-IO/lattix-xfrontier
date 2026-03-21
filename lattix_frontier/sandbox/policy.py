"""Normalized sandbox policy and host-platform detection."""

from __future__ import annotations

from enum import Enum
import platform

from pydantic import BaseModel, Field, model_validator


class HostPlatform(str, Enum):
    """Supported host platforms for sandbox selection."""

    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


class IsolationStrategy(str, Enum):
    """High-level sandboxing strategies used by Frontier."""

    LINUX_HARDENED_CONTAINER = "linux_hardened_container"
    DOCKER_DESKTOP_VM = "docker_desktop_vm"
    WINDOWS_HYPERV_VM = "windows_hyperv_vm"
    GENERIC_DOCKER = "generic_docker"


class BackendCapabilities(BaseModel):
    """Capabilities supported by a sandbox backend."""

    kernel_boundary: bool
    filesystem_confinement: bool
    strict_syscalls: bool
    mediated_egress: bool
    secure_tool_jail: bool
    notes: list[str] = Field(default_factory=list)


def detect_host_platform(system_name: str | None = None) -> HostPlatform:
    """Detect the current host platform."""

    detected = (system_name or platform.system()).strip().lower()
    mapping = {
        "linux": HostPlatform.LINUX,
        "darwin": HostPlatform.MACOS,
        "windows": HostPlatform.WINDOWS,
    }
    return mapping.get(detected, HostPlatform.UNKNOWN)


class SandboxPolicy(BaseModel):
    """Normalized sandbox policy applied before backend-specific planning."""

    name: str = "default"
    platform: HostPlatform = Field(default_factory=detect_host_platform)
    strategy: IsolationStrategy | None = None
    readonly_rootfs: bool = True
    use_tmpfs: bool = True
    allow_network: bool = False
    require_egress_mediation: bool = True
    allowed_hosts: list[str] = Field(default_factory=list)
    allowed_read_paths: list[str] = Field(default_factory=list)
    allowed_write_paths: list[str] = Field(default_factory=list)
    allowed_executables: list[str] = Field(default_factory=list)
    environment_allowlist: list[str] = Field(
        default_factory=lambda: [
            "PATH",
            "TMPDIR",
            "TMP",
            "TEMP",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "NO_PROXY",
        ]
    )
    cpu_limit: float = 1.0
    memory_mb: int = 512
    timeout_seconds: int = 120
    pids_limit: int = 128
    run_as_user: str = "1000:1000"
    seccomp_profile: str | None = None
    apparmor_profile: str | None = None

    @model_validator(mode="after")
    def _apply_platform_defaults(self) -> "SandboxPolicy":
        if self.strategy is None:
            if self.platform == HostPlatform.LINUX:
                self.strategy = IsolationStrategy.LINUX_HARDENED_CONTAINER
            elif self.platform == HostPlatform.MACOS:
                self.strategy = IsolationStrategy.DOCKER_DESKTOP_VM
            elif self.platform == HostPlatform.WINDOWS:
                self.strategy = IsolationStrategy.WINDOWS_HYPERV_VM
            else:
                self.strategy = IsolationStrategy.GENERIC_DOCKER
        return self

    def capabilities(self) -> BackendCapabilities:
        """Return the security posture supported by this policy on the detected platform."""

        if self.platform == HostPlatform.LINUX:
            return BackendCapabilities(
                kernel_boundary=True,
                filesystem_confinement=True,
                strict_syscalls=True,
                mediated_egress=self.require_egress_mediation,
                secure_tool_jail=True,
                notes=["Uses Linux container hardening with Docker seccomp/no-new-privileges/cap-drop."],
            )
        if self.platform in {HostPlatform.MACOS, HostPlatform.WINDOWS}:
            return BackendCapabilities(
                kernel_boundary=True,
                filesystem_confinement=True,
                strict_syscalls=False,
                mediated_egress=self.require_egress_mediation,
                secure_tool_jail=True,
                notes=["Relies on Docker Desktop VM boundary; host-native seccomp parity is not available."],
            )
        return BackendCapabilities(
            kernel_boundary=False,
            filesystem_confinement=True,
            strict_syscalls=False,
            mediated_egress=self.require_egress_mediation,
            secure_tool_jail=True,
            notes=["Unknown host platform; defaulting to generic Docker isolation."],
        )
