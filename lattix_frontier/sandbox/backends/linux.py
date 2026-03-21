"""Linux sandbox backend with hardened Docker options."""

from __future__ import annotations

from lattix_frontier.sandbox.artifacts import WorkspaceLayout
from lattix_frontier.sandbox.backends.docker import DockerSandboxBackend
from lattix_frontier.sandbox.executor import ExecutionSpec, SandboxPlan


class LinuxSandboxBackend(DockerSandboxBackend):
    """Linux backend using Docker hardening and default seccomp enforcement."""

    backend_name = "docker-linux"

    def plan(self, spec: ExecutionSpec, workspace: WorkspaceLayout) -> SandboxPlan:
        egress = self.build_egress_policy(spec)
        command = self._base_docker_command(spec, workspace, egress)
        command.extend(["--cap-drop=ALL", "--security-opt", "no-new-privileges:true"])
        if self.policy.seccomp_profile:
            command.extend(["--security-opt", f"seccomp={self.policy.seccomp_profile}"])
        if self.policy.apparmor_profile:
            command.extend(["--security-opt", f"apparmor={self.policy.apparmor_profile}"])
        return SandboxPlan(
            backend=self.backend_name,
            platform=self.policy.platform,
            strategy=self.policy.strategy,
            docker_command=command,
            network_name=egress.network_name,
            proxy_url=egress.proxy_url,
            workspace_root=str(workspace.root),
            output_mounts=[str(workspace.output_dir)],
            notes=["Linux backend applies cap-drop and no-new-privileges.", "Docker default seccomp remains active unless a custom profile is configured."],
        )
