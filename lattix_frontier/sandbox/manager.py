"""Tool jail service for planning and executing sandboxed tool calls."""

from __future__ import annotations

import asyncio
from pathlib import Path
import uuid

from lattix_frontier.config import Settings, get_settings
from lattix_frontier.events.event_models import AgentEvent
from lattix_frontier.events.nats_client import get_event_bus
from lattix_frontier.security.opa_client import OPAClient
from lattix_frontier.sandbox.artifacts import WorkspaceLayout, cleanup_workspace, collect_outputs, create_workspace, prepare_output_paths, stage_inputs
from lattix_frontier.sandbox.backends.base import SandboxBackend
from lattix_frontier.sandbox.backends.linux import LinuxSandboxBackend
from lattix_frontier.sandbox.backends.macos import MacOSSandboxBackend
from lattix_frontier.sandbox.backends.windows import WindowsSandboxBackend
from lattix_frontier.sandbox.executor import ExecutionResult, ExecutionSpec
from lattix_frontier.sandbox.network import is_host_allowed, normalize_host
from lattix_frontier.sandbox.policy import HostPlatform, SandboxPolicy, detect_host_platform


class ToolJailService:
    """Plan and optionally execute tool invocations inside a sandbox."""

    def __init__(self, settings: Settings | None = None, opa_client: OPAClient | None = None) -> None:
        self.settings = settings or get_settings()
        self.opa_client = opa_client or OPAClient()

    def select_backend(self, policy: SandboxPolicy) -> SandboxBackend:
        """Choose a platform-appropriate backend for the given policy."""

        if policy.platform == HostPlatform.LINUX:
            return LinuxSandboxBackend(policy)
        if policy.platform == HostPlatform.MACOS:
            return MacOSSandboxBackend(policy)
        return WindowsSandboxBackend(policy)

    async def plan(self, spec: ExecutionSpec, policy: SandboxPolicy | None = None) -> ExecutionResult:
        """Create a sandbox plan without executing the tool."""

        active_policy = policy or self._default_policy(spec)
        workspace = self._create_workspace()
        try:
            await self._authorize(spec, active_policy)
            staged_inputs = stage_inputs(workspace, spec.input_paths, active_policy.allowed_read_paths)
            prepare_output_paths(workspace, spec.output_paths)
            backend = self.select_backend(active_policy)
            plan = backend.plan(spec, workspace)
            plan.staged_inputs = staged_inputs
            await self._emit_event("sandbox.plan", {"tool_id": spec.tool_id, "backend": plan.backend})
            return ExecutionResult(executed=False, plan=plan, artifacts=collect_outputs(workspace))
        finally:
            cleanup_workspace(workspace)

    async def execute(self, spec: ExecutionSpec, policy: SandboxPolicy | None = None, dry_run: bool | None = None) -> ExecutionResult:
        """Execute a tool inside the sandbox when live execution is enabled."""

        active_policy = policy or self._default_policy(spec)
        live_execution = self.settings.sandbox_allow_live_execution if dry_run is None else not dry_run
        workspace = self._create_workspace()
        try:
            await self._authorize(spec, active_policy)
            staged_inputs = stage_inputs(workspace, spec.input_paths, active_policy.allowed_read_paths)
            prepare_output_paths(workspace, spec.output_paths)
            backend = self.select_backend(active_policy)
            plan = backend.plan(spec, workspace)
            plan.staged_inputs = staged_inputs
            if not live_execution:
                await self._emit_event("sandbox.plan", {"tool_id": spec.tool_id, "backend": plan.backend})
                return ExecutionResult(executed=False, plan=plan, artifacts=collect_outputs(workspace))
            await self._emit_event("sandbox.execute", {"tool_id": spec.tool_id, "backend": plan.backend})
            return await backend.execute(spec, workspace, plan)
        finally:
            cleanup_workspace(workspace)

    def _default_policy(self, spec: ExecutionSpec) -> SandboxPolicy:
        """Build a default policy for the current host and execution request."""

        return SandboxPolicy(
            platform=detect_host_platform(),
            allowed_hosts=self.settings.allowed_egress_hosts,
            allowed_read_paths=sorted({str(Path(input_path).resolve().parent) for input_path in spec.input_paths}),
            allowed_executables=[spec.command[0]],
            memory_mb=self.settings.sandbox_default_memory_mb,
            cpu_limit=self.settings.sandbox_default_cpu_limit,
            timeout_seconds=self.settings.sandbox_default_timeout_seconds,
            pids_limit=self.settings.sandbox_default_pids_limit,
            allow_network=bool(spec.requested_hosts),
        )

    def _create_workspace(self) -> WorkspaceLayout:
        workspace_root = Path(self.settings.sandbox_workspace_root)
        workspace_root.mkdir(parents=True, exist_ok=True)
        return create_workspace(workspace_root / f"run-{uuid.uuid4().hex}")

    async def _authorize(self, spec: ExecutionSpec, policy: SandboxPolicy) -> None:
        executable = spec.command[0]
        if policy.allowed_executables and executable not in policy.allowed_executables:
            msg = f"Executable not permitted by sandbox policy: {executable}"
            raise PermissionError(msg)
        for input_path in spec.input_paths:
            if not policy.allowed_read_paths:
                msg = "Sandbox policy must explicitly allow input paths before staging host files"
                raise PermissionError(msg)
            decision = await self.opa_client.evaluate(
                "filesystem_access",
                {
                    "action": "read",
                    "path": input_path,
                    "allowed_paths": policy.allowed_read_paths,
                },
            )
            if not decision.allowed:
                msg = f"Filesystem access denied for {input_path}: {decision.reason}"
                raise PermissionError(msg)
        for host in spec.requested_hosts:
            if not is_host_allowed(host, policy.allowed_hosts):
                msg = f"Requested host is not allowlisted by sandbox policy: {normalize_host(host)}"
                raise PermissionError(msg)
            decision = await self.opa_client.evaluate(
                "network_egress",
                {
                    "action": "network_egress",
                    "target": normalize_host(host),
                    "allowed_targets": policy.allowed_hosts,
                },
            )
            if not decision.allowed:
                msg = f"Network egress denied for {host}: {decision.reason}"
                raise PermissionError(msg)
        decision = await self.opa_client.evaluate(
            "tool_jail",
            {
                "readonly_rootfs": policy.readonly_rootfs,
                "require_egress_mediation": policy.require_egress_mediation,
                "allow_network": policy.allow_network,
                "run_as_user": policy.run_as_user,
            },
        )
        if not decision.allowed:
            msg = f"Sandbox policy rejected by tool_jail policy: {decision.reason}"
            raise PermissionError(msg)

    async def _emit_event(self, event_type: str, payload: dict[str, str]) -> None:
        bus = get_event_bus()
        await bus.publish(AgentEvent(event_type=event_type, source="sandbox", payload=payload))
