import asyncio
from pathlib import Path

import pytest

from lattix_frontier.sandbox.executor import ExecutionSpec
from lattix_frontier.sandbox.manager import ToolJailService
from lattix_frontier.sandbox.policy import HostPlatform, SandboxPolicy


def test_tool_jail_plans_linux_hardened_execution(tmp_path: Path) -> None:
    input_file = tmp_path / "input.txt"
    input_file.write_text("hello", encoding="utf-8")
    service = ToolJailService()
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
    assert result.plan.backend == "docker-linux"
    assert result.plan.network_name == "frontier-sandbox-internal"
    assert any("--cap-drop=ALL" == item for item in result.plan.docker_command)


def test_tool_jail_denies_unallowlisted_host() -> None:
    service = ToolJailService()
    spec = ExecutionSpec(tool_id="python", command=["python", "-c", "print('hi')"], requested_hosts=["evil.example.com"])
    policy = SandboxPolicy(
        platform=HostPlatform.LINUX,
        allow_network=True,
        allowed_hosts=["api.example.com"],
        allowed_executables=["python"],
    )
    with pytest.raises(PermissionError):
        asyncio.run(service.plan(spec, policy=policy))
