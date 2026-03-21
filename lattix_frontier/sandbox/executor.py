"""Execution contracts for sandboxed tool runs."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from lattix_frontier.sandbox.policy import HostPlatform, IsolationStrategy


class ExecutionSpec(BaseModel):
    """Request to execute a tool inside a sandbox."""

    tool_id: str
    command: list[str]
    image: str = "python:3.12-slim"
    working_directory: str = "/workspace"
    environment: dict[str, str] = Field(default_factory=dict)
    input_paths: list[str] = Field(default_factory=list)
    output_paths: list[str] = Field(default_factory=list)
    requested_hosts: list[str] = Field(default_factory=list)

    @field_validator("command")
    @classmethod
    def _validate_command(cls, value: list[str]) -> list[str]:
        if not value or not value[0].strip():
            msg = "command must not be empty"
            raise ValueError(msg)
        return value


class SandboxPlan(BaseModel):
    """Resolved backend execution plan."""

    backend: str
    platform: HostPlatform
    strategy: IsolationStrategy
    docker_command: list[str] = Field(default_factory=list)
    network_name: str = "none"
    proxy_url: str | None = None
    workspace_root: str
    staged_inputs: dict[str, str] = Field(default_factory=dict)
    output_mounts: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    """Result of a planned or executed sandbox run."""

    executed: bool = False
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    artifacts: dict[str, str] = Field(default_factory=dict)
    plan: SandboxPlan
