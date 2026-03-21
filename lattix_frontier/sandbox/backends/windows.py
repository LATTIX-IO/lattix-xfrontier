"""Windows sandbox backend using Docker Desktop / Hyper-V VM-backed isolation."""

from __future__ import annotations

from lattix_frontier.sandbox.artifacts import WorkspaceLayout
from lattix_frontier.sandbox.backends.docker import DockerSandboxBackend
from lattix_frontier.sandbox.executor import ExecutionSpec, SandboxPlan


class WindowsSandboxBackend(DockerSandboxBackend):
    """Windows backend that uses Docker's VM-backed boundary and mediated networking."""

    backend_name = "docker-windows"

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
            notes=["Windows backend relies on Docker Desktop / Hyper-V VM-backed isolation.", "Host-native seccomp is not available, so policy enforcement stays at the VM/container boundary."],
        )
