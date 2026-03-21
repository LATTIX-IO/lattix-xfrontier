"""Common Docker-based sandbox backend helpers."""

from __future__ import annotations

import asyncio

from lattix_frontier.config import get_settings
from lattix_frontier.sandbox.artifacts import WorkspaceLayout, collect_outputs
from lattix_frontier.sandbox.executor import ExecutionResult, ExecutionSpec, SandboxPlan
from lattix_frontier.sandbox.network import EgressPolicy
from lattix_frontier.sandbox.policy import SandboxPolicy
from lattix_frontier.sandbox.backends.base import SandboxBackend


class DockerSandboxBackend(SandboxBackend):
    """Common Docker-backed execution planner shared across OS-specific backends."""

    backend_name = "docker"

    def __init__(self, policy: SandboxPolicy) -> None:
        super().__init__(policy)
        self.settings = get_settings()

    def build_egress_policy(self, spec: ExecutionSpec) -> EgressPolicy:
        """Resolve network mediation behavior for the execution."""

        if not self.policy.allow_network:
            return EgressPolicy(network_name="none")
        if self.policy.require_egress_mediation:
            return EgressPolicy(
                allowed_hosts=self.policy.allowed_hosts,
                proxy_url=f"http://{self.settings.sandbox_egress_gateway}",
                network_name=self.settings.sandbox_internal_network,
            )
        return EgressPolicy(allowed_hosts=self.policy.allowed_hosts, network_name="bridge")

    def _base_docker_command(self, spec: ExecutionSpec, workspace: WorkspaceLayout, egress: EgressPolicy) -> list[str]:
        command = [
            "docker",
            "run",
            "--rm",
            "--workdir",
            spec.working_directory,
            "--memory",
            f"{self.policy.memory_mb}m",
            "--cpus",
            str(self.policy.cpu_limit),
            "--pids-limit",
            str(self.policy.pids_limit),
            "--user",
            self.policy.run_as_user,
            "--network",
            egress.network_name,
            "--mount",
            f"type=bind,src={workspace.input_dir},dst=/workspace/input,readonly",
            "--mount",
            f"type=bind,src={workspace.output_dir},dst=/workspace/output",
        ]
        if self.policy.readonly_rootfs:
            command.append("--read-only")
        if self.policy.use_tmpfs:
            command.extend(["--tmpfs", "/tmp:rw,noexec,nosuid,size=64m"])
        if egress.proxy_url is not None:
            command.extend(["-e", f"HTTP_PROXY={egress.proxy_url}", "-e", f"HTTPS_PROXY={egress.proxy_url}"])
        for key, value in spec.environment.items():
            if key in self.policy.environment_allowlist:
                command.extend(["-e", f"{key}={value}"])
        command.append(spec.image)
        command.extend(spec.command)
        return command

    async def execute(self, spec: ExecutionSpec, workspace: WorkspaceLayout, plan: SandboxPlan) -> ExecutionResult:
        """Execute the Docker plan when live execution is enabled."""

        process = await asyncio.create_subprocess_exec(
            *plan.docker_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=self.policy.timeout_seconds)
        except TimeoutError:
            process.kill()
            await process.wait()
            return ExecutionResult(
                executed=True,
                exit_code=124,
                stdout="",
                stderr="sandbox execution timed out",
                artifacts=collect_outputs(workspace),
                plan=plan,
            )
        return ExecutionResult(
            executed=True,
            exit_code=process.returncode,
            stdout=stdout_bytes.decode("utf-8", errors="replace"),
            stderr=stderr_bytes.decode("utf-8", errors="replace"),
            artifacts=collect_outputs(workspace),
            plan=plan,
        )
