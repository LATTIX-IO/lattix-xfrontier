from __future__ import annotations

import os
import platform
from pathlib import Path

import click

from . import installer
from .common import (
    DEFAULT_ARCHIVE_URL,
    detect_sandbox_backend,
    discover_agent_records,
    ensure_compose_env_file,
    print_json,
    python_executable,
    repo_root,
    request_json,
    resolve_opa_command,
    run_command,
)

ROOT = repo_root()


def _full_compose(*extra: str) -> list[str]:
    env_path = ensure_compose_env_file()
    return ["docker", "compose", "--env-file", str(env_path), *extra]


def _local_compose(*extra: str) -> list[str]:
    env_path = ensure_compose_env_file()
    return ["docker", "compose", "--env-file", str(env_path), "-f", "docker-compose.local.yml", *extra]


@click.group()
def cli() -> None:
    """Lattix xFrontier repo tooling."""


@cli.command()
def bootstrap() -> None:
    run_command([python_executable(), "-m", "pip", "install", "-e", ".[dev]"], cwd=ROOT)
    run_command(_full_compose("pull"), cwd=ROOT)
    click.echo("Run 'lattix dev' to start the secure platform stack.")


@cli.command("dev")
def dev_command() -> None:
    run_command(_full_compose("up", "-d"), cwd=ROOT)
    click.echo("Secure platform stack running. Gateway: http://frontier.localhost ; API health: http://localhost:8000/healthz")


@cli.command("up")
def up_command() -> None:
    run_command(_full_compose("up", "-d"), cwd=ROOT)


@cli.command("down")
def down_command() -> None:
    run_command(_full_compose("down", "-v"), cwd=ROOT)


@cli.command("stack-up")
def stack_up_command() -> None:
    run_command(_full_compose("up", "-d"), cwd=ROOT)


@cli.command("stack-down")
def stack_down_command() -> None:
    run_command(_full_compose("down", "-v"), cwd=ROOT)


@cli.command("local-up")
def local_up_command() -> None:
    run_command(_local_compose("up", "-d"), cwd=ROOT)
    click.echo("Lightweight local stack running. Frontend: http://localhost:3000 ; API health: http://localhost:8000/healthz")


@cli.command("local-down")
def local_down_command() -> None:
    run_command(_local_compose("down", "-v"), cwd=ROOT)


@cli.command()
def ps() -> None:
    run_command(_full_compose("ps"), cwd=ROOT)


@cli.command()
def logs() -> None:
    run_command(_full_compose("logs", "--tail=200"), cwd=ROOT)


@cli.command()
def health() -> None:
    print_json(request_json("http://localhost:8000/healthz"))


@cli.command()
def smoke() -> None:
    print_json(request_json("http://localhost:8000/healthz"))


@cli.command()
def test() -> None:
    run_command([python_executable(), "-m", "pytest", "tests", "-v"], cwd=ROOT / "apps" / "backend")


@cli.command()
def lint() -> None:
    run_command([python_executable(), "-m", "ruff", "check", ".", "--fix"], cwd=ROOT)
    run_command([python_executable(), "-m", "ruff", "format", "."], cwd=ROOT)


@cli.command()
def typecheck() -> None:
    run_command([python_executable(), "-m", "mypy", "frontier_tooling"], cwd=ROOT)


@cli.group()
def policy() -> None:
    """OPA policy helpers."""


@policy.command("test")
def policy_test() -> None:
    run_command([python_executable(), "scripts/run_opa.py", "test", "policies/", "-v"], cwd=ROOT)


@policy.command("lint")
def policy_lint() -> None:
    run_command([resolve_opa_command(), "check", "policies/"], cwd=ROOT)


@cli.command("install-opa")
def install_opa() -> None:
    if os.name != "nt":
        click.echo("Automatic OPA installation is currently implemented in the PowerShell helper on Windows. Install 'opa' on PATH or place it under .tools/opa/.")
        return
    opa_dir = ROOT / ".tools" / "opa"
    opa_dir.mkdir(parents=True, exist_ok=True)
    opa_path = opa_dir / "opa.exe"
    run_command(
        [
            python_executable(),
            "-c",
            (
                "from urllib.request import urlopen; from pathlib import Path; "
                f"data=urlopen('https://openpolicyagent.org/downloads/v0.68.0/opa_windows_amd64.exe').read(); "
                f"Path(r'{opa_path}').write_bytes(data)"
            ),
        ],
        cwd=ROOT,
    )
    click.echo(str(opa_path))


@cli.group()
def agent() -> None:
    """Agent asset helpers."""


@agent.command("list")
def agent_list() -> None:
    print_json(discover_agent_records())


@agent.command("scaffold")
@click.option("--name", required=True)
def agent_scaffold(name: str) -> None:
    run_command([python_executable(), "apps/workers/scripts/scaffold_agent_service.py", name], cwd=ROOT)


@cli.group()
def workflow() -> None:
    """Workflow helpers."""


@workflow.command("list")
def workflow_list() -> None:
    print_json(request_json("http://localhost:8000/workflow-definitions"))


@workflow.command("run")
@click.argument("workflow_name")
@click.option("--task", required=True)
def workflow_run(workflow_name: str, task: str) -> None:
    payload = {"workflow_definition_id": workflow_name, "task": task, "input": {"task": task}}
    print_json(request_json("http://localhost:8000/workflow-runs", method="POST", payload=payload))


@cli.group()
def sandbox() -> None:
    """Sandbox helpers."""


@sandbox.command("backend")
def sandbox_backend() -> None:
    print_json({"backend": detect_sandbox_backend(), "platform": platform.system()})


@cli.group()
def install() -> None:
    """Installer helpers."""


@install.command("run")
def install_run() -> None:
    installer.main()


@install.command("bootstrap-url")
def install_bootstrap_url() -> None:
    click.echo(installer.bootstrap_url() or DEFAULT_ARCHIVE_URL)


@cli.command()
@click.argument("domain", required=False)
def demo(domain: str | None) -> None:
    print_json({"domain": domain or "default", "agents": discover_agent_records()[:5]})


if __name__ == "__main__":
    cli()
