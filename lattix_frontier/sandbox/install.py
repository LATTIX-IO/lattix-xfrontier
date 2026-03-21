"""Host-capability detection helpers for future sandbox installation workflows."""

from __future__ import annotations

from pydantic import BaseModel, Field

from lattix_frontier.sandbox.policy import HostPlatform, detect_host_platform


class InstallRecommendation(BaseModel):
    """Recommended sandbox prerequisites for the detected host."""

    platform: HostPlatform
    packages: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def recommend_installation(platform_name: HostPlatform | None = None) -> InstallRecommendation:
    """Return platform-specific prerequisites for the sandbox runtime."""

    platform_value = platform_name or detect_host_platform()
    if platform_value == HostPlatform.LINUX:
        return InstallRecommendation(
            platform=platform_value,
            packages=["docker", "docker-compose-plugin"],
            notes=["Enable Docker with default seccomp and user namespaces where available."],
        )
    if platform_value == HostPlatform.MACOS:
        return InstallRecommendation(
            platform=platform_value,
            packages=["Docker Desktop"],
            notes=["Docker Desktop provides the VM-backed boundary used by the macOS sandbox backend."],
        )
    if platform_value == HostPlatform.WINDOWS:
        return InstallRecommendation(
            platform=platform_value,
            packages=["Docker Desktop", "Hyper-V"],
            notes=["Prefer Hyper-V-backed Docker Desktop for the Windows sandbox backend."],
        )
    return InstallRecommendation(platform=platform_value, notes=["Unknown platform; default to generic Docker support."])
