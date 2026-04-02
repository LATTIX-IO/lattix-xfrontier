import asyncio
from pathlib import Path

import pytest

from frontier_runtime.sandbox import (
    ExecutionSpec,
    HostPlatform,
    IsolationStrategy,
    SandboxManager,
    SandboxPolicy,
    ToolJailService,
)


def test_tool_jail_plans_linux_hardened_execution(tmp_path: Path) -> None:
    input_file = tmp_path / "input.txt"
    input_file.write_text("hello", encoding="utf-8")
    # Force hardened-docker strategy so the test is deterministic regardless
    # of whether bwrap is installed on the CI host.
    manager = SandboxManager(force_strategy=IsolationStrategy.HARDENED_DOCKER)
    service = ToolJailService(manager=manager)
    spec = ExecutionSpec(
        tool_id="python",
        command=["python", "-c", "print('hi')"],
        input_paths=[str(input_file)],
        output_paths=["result.txt"],
        requested_hosts=["api.example.com"],
    )
    policy = SandboxPolicy(
        platform=HostPlatform.LINUX,
        allow_network=True,
        allowed_hosts=["api.example.com"],
        allowed_read_paths=[str(tmp_path)],
        allowed_executables=["python"],
    )
    result = asyncio.run(service.plan(spec, policy=policy))
    assert result.executed is False
    assert result.plan.backend == "hardened-docker"
    assert result.plan.network_name == "frontier-sandbox-internal"
    cmd = result.plan.docker_command
    assert "--cap-drop=ALL" in cmd
    assert "--read-only" in cmd
    assert "--user=1000:1000" in cmd
    assert "--ipc=private" in cmd


def test_tool_jail_denies_unallowlisted_host() -> None:
    manager = SandboxManager(force_strategy=IsolationStrategy.HARDENED_DOCKER)
    service = ToolJailService(manager=manager)
    spec = ExecutionSpec(
        tool_id="python",
        command=["python", "-c", "print('hi')"],
        requested_hosts=["evil.example.com"],
    )
    policy = SandboxPolicy(
        platform=HostPlatform.LINUX,
        allow_network=True,
        allowed_hosts=["api.example.com"],
        allowed_executables=["python"],
    )
    with pytest.raises(PermissionError):
        asyncio.run(service.plan(spec, policy=policy))
