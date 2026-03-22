"""Click-based CLI entrypoint for the Frontier root platform."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
import sys

import click
import httpx

from lattix_frontier.agents.registry import AgentRegistry, build_default_registry
from lattix_frontier.agents.templates.scaffold import scaffold_agent
from lattix_frontier.orchestrator.workflows import get_workflow_catalog
from lattix_frontier.install.installer import FrontierInstaller
from lattix_frontier.sandbox.executor import ExecutionSpec
from lattix_frontier.sandbox.install import recommend_installation
from lattix_frontier.sandbox.manager import ToolJailService


def _run_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


@click.group()
def cli() -> None:
    """Lattix xFrontier CLI."""


@cli.command()
def dev() -> None:
    """Start the local Docker Compose stack."""

    _run_command(["docker", "compose", "up", "-d"])
    click.echo("Stack running. Admin UI: http://localhost:8000")


@cli.group()
def agent() -> None:
    """Agent management commands."""


@agent.command("list")
def agent_list() -> None:
    """List registered agents."""

    registry = build_default_registry()
    click.echo(json.dumps([item.model_dump() for item in registry.list_agents()], indent=2))


@agent.command("scaffold")
@click.option("--name", required=True, help="Agent directory name.")
@click.option("--destination", default="generated-agents", show_default=True)
def agent_scaffold(name: str, destination: str) -> None:
    """Scaffold a new agent from the built-in template."""

    output = scaffold_agent(name=name, destination=Path(destination))
    click.echo(str(output))


@cli.group()
def workflow() -> None:
    """Workflow commands."""


@workflow.command("list")
def workflow_list() -> None:
    """List available workflows."""

    catalog = get_workflow_catalog()
    click.echo(json.dumps(sorted(catalog.keys()), indent=2))


@workflow.command("run")
@click.argument("name")
@click.option("--task", required=True, help="Task to execute.")
def workflow_run(name: str, task: str) -> None:
    """Execute a workflow by name."""

    catalog = get_workflow_catalog()
    workflow_obj = catalog[name]
    result = asyncio.run(workflow_obj.run(task=task))
    click.echo(result.final_output or "")


@cli.group()
def policy() -> None:
    """Policy lifecycle commands."""


@policy.command("test")
def policy_test() -> None:
    """Run OPA policy tests."""

    _run_command(["opa", "test", "policies/", "-v"])


@policy.command("lint")
def policy_lint() -> None:
    """Validate Rego policy files exist and are non-empty."""

    policy_dir = Path("policies")
    rego_files = sorted(policy_dir.glob("*.rego"))
    if not rego_files:
        raise click.ClickException("No policy files found.")
    invalid = [path for path in rego_files if not path.read_text(encoding="utf-8").strip()]
    if invalid:
        names = ", ".join(str(path) for path in invalid)
        raise click.ClickException(f"Empty policy files: {names}")
    click.echo(f"Validated {len(rego_files)} policy files.")


@cli.command()
def health() -> None:
    """Check health of the local orchestrator API."""

    async def _health() -> dict[str, str]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/health")
            response.raise_for_status()
            return response.json()

    click.echo(json.dumps(asyncio.run(_health()), indent=2))


@cli.command()
@click.argument("domain")
def demo(domain: str) -> None:
    """Run a demo workflow for a given domain."""

    catalog = get_workflow_catalog()
    workflow_name = {
        "gtm": "gtm_content",
        "security": "security_compliance",
        "ops": "ops_project",
    }.get(domain, domain)
    if workflow_name not in catalog:
        raise click.ClickException(f"Unknown demo domain: {domain}")
    result = asyncio.run(catalog[workflow_name].run(task=f"demo:{domain}"))
    click.echo(result.final_output or "")


@cli.group()
def sandbox() -> None:
    """Sandbox planning and host-capability commands."""


@sandbox.command("backend")
def sandbox_backend() -> None:
    """Show the detected sandbox backend recommendation."""

    recommendation = recommend_installation()
    click.echo(recommendation.model_dump_json(indent=2))


@sandbox.command("plan")
@click.option("--tool-id", required=True, help="Registered tool identifier.")
@click.option("--image", default="python:3.12-slim", show_default=True)
@click.option("--host", "hosts", multiple=True, help="Allowlisted egress host. Repeat as needed.")
@click.argument("command", nargs=-1, required=True)
def sandbox_plan(tool_id: str, image: str, hosts: tuple[str, ...], command: tuple[str, ...]) -> None:
    """Create a dry-run sandbox plan for a tool command."""

    service = ToolJailService()
    spec = ExecutionSpec(tool_id=tool_id, image=image, command=list(command), requested_hosts=list(hosts))
    result = asyncio.run(service.plan(spec))
    click.echo(result.model_dump_json(indent=2))


@cli.group()
def install() -> None:
    """Installer and distribution commands."""


@install.command("run")
def install_run() -> None:
    """Run the interactive Frontier installer."""

    raise SystemExit(FrontierInstaller().run())


@install.command("bootstrap-url")
def install_bootstrap_url() -> None:
    """Print the curl/PowerShell bootstrap commands for public distribution."""

    click.echo("curl -fsSL https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/bootstrap.sh | sh")
    if sys.platform.startswith("win"):
        click.echo("powershell -ExecutionPolicy Bypass -c \"iwr https://raw.githubusercontent.com/LATTIX-IO/lattix-xfrontier/main/install/bootstrap.ps1 | iex\"")
