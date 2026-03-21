"""macOS sandbox backend using Docker Desktop's Linux VM boundary."""

from __future__ import annotations

from lattix_frontier.sandbox.artifacts import WorkspaceLayout
from lattix_frontier.sandbox.backends.docker import DockerSandboxBackend
from lattix_frontier.sandbox.executor import ExecutionSpec, SandboxPlan


class MacOSSandboxBackend(DockerSandboxBackend):
    """macOS backend that relies on Docker Desktop VM-backed isolation."""

    backend_name = "docker-macos"

    def plan(self, spec: ExecutionSpec, workspace: WorkspaceLayout) -> SandboxPlan:
        egress = self.build_egress_policy(spec)
        command = self._base_docker_command(spec, workspace, egress)
        return SandboxPlan(
            backend=self.backend_name,
            platform=self.policy.platform,
            strategy=self.policy.strategy,
            docker_command=command,
            network_name=egress.network_name,
            proxy_url=egress.proxy_url,
            workspace_root=str(workspace.root),
            output_mounts=[str(workspace.output_dir)],
            notes=["macOS backend relies on Docker Desktop's Linux VM for kernel isolation.", "Linux-only seccomp and AppArmor options are omitted on macOS hosts."],
        )
