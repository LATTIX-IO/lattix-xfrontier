"""Interactive installer for local and enterprise Frontier deployments."""

from __future__ import annotations

from dataclasses import dataclass
import getpass
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import subprocess
import sys
from typing import Any

from pydantic import BaseModel, Field

from lattix_frontier.config import get_settings
from lattix_frontier.install.diagnostics import (
    DiagnosticResult,
    command_available,
    docker_compose_available,
    docker_daemon_available,
    helm_available,
    hostname_prefix_valid,
    kubectl_available,
    port_available,
    writable_directory,
)
from lattix_frontier.sandbox.install import InstallRecommendation, recommend_installation


@dataclass(frozen=True, slots=True)
class PrerequisiteDefinition:
    """Descriptor for a prerequisite that can be checked and optionally installed."""

    key: str
    display_name: str
    check_name: str
    install_commands: tuple[tuple[str, ...], ...]
    manual_steps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MissingPrerequisite:
    """A prerequisite check that did not pass."""

    definition: PrerequisiteDefinition
    result: DiagnosticResult


class InstallerAnswers(BaseModel):
    """Persisted user selections for installer runs."""

    installation_root: str
    deployment_mode: str = "local"
    local_hostname: str = "frontier"
    enable_local_launch: bool = True
    openai_api_key: str = ""
    openai_model: str = "gpt-5.2"
    sandbox_live_execution: bool = False
    enterprise_namespace: str = "lattix"
    enterprise_ingress_host: str = "frontier.example.com"
    federation_enabled: bool = False
    federation_cluster_name: str = "frontier-cluster"
    federation_region: str = "us-east"
    federation_peers: list[str] = Field(default_factory=list)


class FrontierInstaller:
    """Interactive installer that prepares local or enterprise deployment artifacts."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self.settings = get_settings()
        self.repo_root = repo_root or Path.cwd()
        self.state_dir = self.repo_root / ".installer"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> int:
        """Execute the interactive installer flow."""

        self._print_header()
        recommendation = recommend_installation()
        self._print_step("Detected platform", recommendation.model_dump())
        self._validate_prerequisites(recommendation)
        answers = self._collect_answers()
        self._validate_answers(answers)
        local_secrets = self._collect_local_secrets(answers)
        self._write_answers(answers)
        env_path = self._write_env_file(answers, local_secrets)
        self._write_generated_helm_values(answers)
        self._print_step("Configuration written", {"env": str(env_path)})
        if answers.deployment_mode in {"local", "both"}:
            self._maybe_launch_local(answers)
            self._print_local_access(answers)
        if answers.deployment_mode in {"enterprise", "both"}:
            self._print_enterprise_access(answers)
        return 0

    def _print_header(self) -> None:
        print("==> Lattix Frontier installer")  # noqa: T201
        print("==> This installer will configure your preferred local and/or enterprise deployment.")  # noqa: T201

    def _print_step(self, title: str, payload: dict[str, Any]) -> None:
        print(f"==> {title}")  # noqa: T201
        print(json.dumps(payload, indent=2))  # noqa: T201

    def _validate_prerequisites(self, recommendation: InstallRecommendation) -> None:
        missing = self._collect_missing_prerequisites(recommendation.packages)
        self._resolve_missing_prerequisites(
            missing,
            intro="The installer needs a few host prerequisites before it can continue.",
        )
        docker_result = docker_daemon_available()
        self._print_diagnostic(docker_result)
        if not docker_result.ok:
            self._abort_with_actionable_guidance(
                intro="Docker is installed, but the runtime is not ready yet.",
                missing=[
                    MissingPrerequisite(
                        definition=PrerequisiteDefinition(
                            key="docker-daemon",
                            display_name="Docker daemon",
                            check_name="docker-daemon",
                            install_commands=(),
                            manual_steps=(
                                "Start Docker Desktop or the docker service so `docker info` succeeds.",
                                "After Docker reports a running daemon, rerun the installer.",
                            ),
                        ),
                        result=docker_result,
                    )
                ],
            )

    def _print_diagnostic(self, result: DiagnosticResult) -> None:
        status = "ok" if result.ok else "failed"
        print(f"==> Diagnostic {result.name}: {status} - {result.message}")  # noqa: T201

    def _collect_missing_prerequisites(self, package_names: list[str]) -> list[MissingPrerequisite]:
        missing: list[MissingPrerequisite] = []
        seen: set[str] = set()
        for package_name in package_names:
            definition = self._get_prerequisite_definition(package_name)
            if definition is None or definition.key in seen:
                continue
            seen.add(definition.key)
            result = self._run_prerequisite_check(definition)
            self._print_diagnostic(result)
            if not result.ok:
                missing.append(MissingPrerequisite(definition=definition, result=result))
        return missing

    def _resolve_missing_prerequisites(self, missing: list[MissingPrerequisite], intro: str) -> None:
        if not missing:
            return
        print(f"==> {intro}")  # noqa: T201
        for item in missing:
            print(f"   - {item.definition.display_name}: {item.result.message}")  # noqa: T201
        should_install = self._ask_yes_no(
            "Attempt automatic installation for the missing prerequisites where supported?",
            default=True,
        )
        unresolved = missing
        if should_install:
            unresolved = self._attempt_missing_prerequisite_installs(missing)
        if unresolved:
            if not should_install:
                print("==> Automatic installation skipped at your request.")  # noqa: T201
            self._abort_with_actionable_guidance(
                intro="The installer cannot continue until the required prerequisites are available.",
                missing=unresolved,
            )

    def _attempt_missing_prerequisite_installs(
        self,
        missing: list[MissingPrerequisite],
    ) -> list[MissingPrerequisite]:
        unresolved: list[MissingPrerequisite] = []
        for item in missing:
            definition = item.definition
            print(f"==> Attempting installation for {definition.display_name}")  # noqa: T201
            if not definition.install_commands:
                unresolved.append(
                    MissingPrerequisite(
                        definition=definition,
                        result=DiagnosticResult(
                            name=definition.check_name,
                            ok=False,
                            message="automatic installation is not supported on this host",
                        ),
                    )
                )
                continue
            install_failed = False
            failure_message = "automatic installation failed"
            for command in definition.install_commands:
                completed = self._run_install_command(command)
                if completed.returncode != 0:
                    detail = completed.stderr.strip() or completed.stdout.strip()
                    failure_message = detail or f"{' '.join(command)} exited with code {completed.returncode}"
                    install_failed = True
                    break
            if install_failed:
                unresolved.append(
                    MissingPrerequisite(
                        definition=definition,
                        result=DiagnosticResult(
                            name=definition.check_name,
                            ok=False,
                            message=failure_message,
                        ),
                    )
                )
                continue
            recheck = self._run_prerequisite_check(definition)
            self._print_diagnostic(recheck)
            if not recheck.ok:
                unresolved.append(MissingPrerequisite(definition=definition, result=recheck))
        return unresolved

    def _run_install_command(self, command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, capture_output=True, check=False, text=True)

    def _run_prerequisite_check(self, definition: PrerequisiteDefinition) -> DiagnosticResult:
        if definition.check_name == "command:docker":
            return command_available("docker")
        if definition.check_name == "docker-compose-plugin":
            return docker_compose_available()
        if definition.check_name == "command:helm":
            return helm_available()
        if definition.check_name == "command:kubectl":
            return kubectl_available()
        return DiagnosticResult(name=definition.check_name, ok=False, message="unknown prerequisite check")

    def _get_prerequisite_definition(self, package_name: str) -> PrerequisiteDefinition | None:
        platform_key = self._host_platform_key()
        if package_name in {"Docker Desktop", "docker"}:
            return PrerequisiteDefinition(
                key="docker",
                display_name="Docker",
                check_name="command:docker",
                install_commands=self._install_commands_for("docker", platform_key),
                manual_steps=self._manual_steps_for("docker", platform_key),
            )
        if package_name == "docker-compose-plugin":
            return PrerequisiteDefinition(
                key="docker-compose-plugin",
                display_name="Docker Compose v2 plugin",
                check_name="docker-compose-plugin",
                install_commands=self._install_commands_for("docker-compose-plugin", platform_key),
                manual_steps=self._manual_steps_for("docker-compose-plugin", platform_key),
            )
        if package_name == "helm":
            return PrerequisiteDefinition(
                key="helm",
                display_name="Helm",
                check_name="command:helm",
                install_commands=self._install_commands_for("helm", platform_key),
                manual_steps=self._manual_steps_for("helm", platform_key),
            )
        if package_name == "kubectl":
            return PrerequisiteDefinition(
                key="kubectl",
                display_name="kubectl",
                check_name="command:kubectl",
                install_commands=self._install_commands_for("kubectl", platform_key),
                manual_steps=self._manual_steps_for("kubectl", platform_key),
            )
        if package_name == "Hyper-V":
            return None
        return None

    def _host_platform_key(self) -> str:
        if sys.platform.startswith("win"):
            return "windows"
        if sys.platform == "darwin":
            return "macos"
        return "linux"

    def _install_commands_for(self, key: str, platform_key: str) -> tuple[tuple[str, ...], ...]:
        commands = {
            "windows": {
                "docker": {
                    "winget": ((
                        "winget",
                        "install",
                        "-e",
                        "--id",
                        "Docker.DockerDesktop",
                        "--accept-package-agreements",
                        "--accept-source-agreements",
                    ),),
                    "choco": (("choco", "install", "docker-desktop", "-y"),),
                },
                "helm": {
                    "winget": ((
                        "winget",
                        "install",
                        "-e",
                        "--id",
                        "Helm.Helm",
                        "--accept-package-agreements",
                        "--accept-source-agreements",
                    ),),
                    "choco": (("choco", "install", "kubernetes-helm", "-y"),),
                },
                "kubectl": {
                    "winget": ((
                        "winget",
                        "install",
                        "-e",
                        "--id",
                        "Kubernetes.kubectl",
                        "--accept-package-agreements",
                        "--accept-source-agreements",
                    ),),
                    "choco": (("choco", "install", "kubernetes-cli", "-y"),),
                },
            },
            "macos": {
                "docker": {"brew": (("brew", "install", "--cask", "docker"),)},
                "docker-compose-plugin": {"brew": (("brew", "install", "docker-compose"),)},
                "helm": {"brew": (("brew", "install", "helm"),)},
                "kubectl": {"brew": (("brew", "install", "kubectl"),)},
            },
            "linux": {
                "docker": {
                    "apt-get": (("sudo", "apt-get", "update"), ("sudo", "apt-get", "install", "-y", "docker.io")),
                    "dnf": (("sudo", "dnf", "install", "-y", "docker"),),
                    "yum": (("sudo", "yum", "install", "-y", "docker"),),
                },
                "docker-compose-plugin": {
                    "apt-get": (("sudo", "apt-get", "install", "-y", "docker-compose-plugin"),),
                    "dnf": (("sudo", "dnf", "install", "-y", "docker-compose-plugin"),),
                    "yum": (("sudo", "yum", "install", "-y", "docker-compose-plugin"),),
                },
                "helm": {"brew": (("brew", "install", "helm"),)},
                "kubectl": {
                    "apt-get": (("sudo", "apt-get", "install", "-y", "kubectl"),),
                    "dnf": (("sudo", "dnf", "install", "-y", "kubectl"),),
                    "yum": (("sudo", "yum", "install", "-y", "kubectl"),),
                    "brew": (("brew", "install", "kubectl"),),
                },
            },
        }
        for manager in self._available_package_managers(platform_key):
            selected = commands.get(platform_key, {}).get(key, {}).get(manager)
            if selected:
                return selected
        return ()

    def _manual_steps_for(self, key: str, platform_key: str) -> tuple[str, ...]:
        if key == "docker":
            if platform_key == "windows":
                return (
                    "Install Docker Desktop and ensure the `docker` CLI is available on PATH.",
                    "Start Docker Desktop, wait for it to report a running engine, then rerun the installer.",
                )
            if platform_key == "macos":
                return (
                    "Install Docker Desktop for macOS and confirm `docker version` works in a new terminal.",
                    "Start Docker Desktop before rerunning the installer.",
                )
            return (
                "Install Docker Engine for your Linux distribution and confirm `docker version` works.",
                "Start the Docker service before rerunning the installer.",
            )
        if key == "docker-compose-plugin":
            return (
                "Install Docker Compose v2 so `docker compose version` succeeds.",
                "After the Compose plugin is available, rerun the installer.",
            )
        if key == "helm":
            return (
                "Install Helm and confirm `helm version` works from your shell.",
                "After Helm is available on PATH, rerun the installer.",
            )
        if key == "kubectl":
            return (
                "Install kubectl and confirm `kubectl version --client` works from your shell.",
                "After kubectl is available on PATH, rerun the installer.",
            )
        return ("Install the missing prerequisite and rerun the installer.",)

    def _available_package_managers(self, platform_key: str) -> list[str]:
        candidates = {
            "windows": ["winget", "choco"],
            "macos": ["brew"],
            "linux": ["apt-get", "dnf", "yum", "brew"],
        }
        available: list[str] = []
        for name in candidates.get(platform_key, []):
            if shutil.which(name) is not None:
                available.append(name)
        return available

    def _abort_with_actionable_guidance(self, intro: str, missing: list[MissingPrerequisite]) -> None:
        lines = [intro, "", "Outstanding prerequisites:"]
        for item in missing:
            lines.append(f"- {item.definition.display_name}: {item.result.message}")
            suggested = self._suggest_install_command(item.definition)
            if suggested:
                lines.append(f"  Next step: run {' '.join(suggested)} and rerun the installer.")
            for step in item.definition.manual_steps:
                lines.append(f"  Next step: {step}")
        raise SystemExit("\n".join(lines))

    def _suggest_install_command(self, definition: PrerequisiteDefinition) -> tuple[str, ...] | None:
        if not definition.install_commands:
            return None
        return definition.install_commands[-1]

    def _collect_answers(self) -> InstallerAnswers:
        installation_root = self._ask("Install directory", default=str(self.repo_root))
        deployment_mode = self._ask_choice("Deployment mode", ["local", "enterprise", "both"], default="local")
        local_hostname = self._ask("Local hostname prefix", default="frontier")
        launch_local = self._ask_yes_no("Launch local stack when setup completes?", default=True)
        sandbox_live_execution = self._ask_yes_no("Allow live sandbox tool execution?", default=False)
        openai_api_key = getpass.getpass("OpenAI API key (leave blank to skip): ")
        openai_model = self._ask("OpenAI model", default="gpt-5.2")
        enterprise_namespace = self._ask("Kubernetes namespace", default="lattix")
        enterprise_ingress_host = self._ask("Enterprise ingress host", default="frontier.example.com")
        federation_enabled = self._ask_yes_no("Enable distributed federation settings?", default=False)
        federation_cluster_name = self._ask("Federation cluster name", default="frontier-cluster")
        federation_region = self._ask("Federation region", default="us-east")
        peers_input = self._ask("Federation peers (comma separated URLs)", default="")
        return InstallerAnswers(
            installation_root=installation_root,
            deployment_mode=deployment_mode,
            local_hostname=local_hostname,
            enable_local_launch=launch_local,
            openai_api_key=openai_api_key,
            openai_model=openai_model,
            sandbox_live_execution=sandbox_live_execution,
            enterprise_namespace=enterprise_namespace,
            enterprise_ingress_host=enterprise_ingress_host,
            federation_enabled=federation_enabled,
            federation_cluster_name=federation_cluster_name,
            federation_region=federation_region,
            federation_peers=[item.strip() for item in peers_input.split(",") if item.strip()],
        )

    def _collect_local_secrets(self, answers: InstallerAnswers) -> dict[str, str]:
        """Prompt for or generate local-only secrets that must not be persisted in answers.json."""

        if answers.deployment_mode not in {"local", "both"}:
            return {}
        provided = getpass.getpass("A2A JWT secret (leave blank to auto-generate securely for local deployment): ").strip()
        generated = not bool(provided)
        secret_value = provided or secrets.token_urlsafe(48)
        if generated:
            print("==> Generated a new local A2A JWT secret and stored it in the installer-managed env file.")  # noqa: T201
        return {"A2A_JWT_SECRET": secret_value}

    def _ask(self, prompt: str, default: str = "") -> str:
        suffix = f" [{default}]" if default else ""
        value = input(f"{prompt}{suffix}: ").strip()
        return value or default

    def _ask_yes_no(self, prompt: str, default: bool) -> bool:
        default_label = "Y/n" if default else "y/N"
        value = input(f"{prompt} ({default_label}): ").strip().lower()
        if not value:
            return default
        return value in {"y", "yes"}

    def _ask_choice(self, prompt: str, options: list[str], default: str) -> str:
        value = self._ask(f"{prompt} ({'/'.join(options)})", default=default)
        if value not in options:
            msg = f"Invalid choice '{value}'. Expected one of: {', '.join(options)}"
            raise SystemExit(msg)
        return value

    def _validate_answers(self, answers: InstallerAnswers) -> None:
        installation_root_result = writable_directory(Path(answers.installation_root))
        self._print_diagnostic(installation_root_result)
        if not installation_root_result.ok:
            raise SystemExit(installation_root_result.message)
        hostname_result = hostname_prefix_valid(answers.local_hostname)
        self._print_diagnostic(hostname_result)
        if not hostname_result.ok:
            raise SystemExit(hostname_result.message)
        if answers.deployment_mode in {"local", "both"} and answers.enable_local_launch:
            port_result = port_available(self.settings.local_gateway_http_port)
            self._print_diagnostic(port_result)
            if not port_result.ok:
                raise SystemExit(port_result.message)
        if answers.deployment_mode in {"enterprise", "both"}:
            enterprise_missing = self._collect_missing_prerequisites(["helm", "kubectl"])
            self._resolve_missing_prerequisites(
                enterprise_missing,
                intro="Enterprise deployment needs Kubernetes CLI tools before Helm manifests can be applied.",
            )

    def _write_answers(self, answers: InstallerAnswers) -> Path:
        answers_path = self.state_dir / "answers.json"
        answers_path.write_text(answers.model_dump_json(indent=2), encoding="utf-8")
        return answers_path

    def _write_env_file(self, answers: InstallerAnswers, local_secrets: dict[str, str]) -> Path:
        env_example = self.repo_root / ".env.example"
        env_path = self.state_dir / "local.env"
        base_lines = env_example.read_text(encoding="utf-8").splitlines() if env_example.exists() else []
        managed = {
            "OPENAI_API_KEY": answers.openai_api_key,
            "OPENAI_MODEL": answers.openai_model,
            "LOCAL_STACK_HOST": f"{answers.local_hostname}.localhost",
            "NEXT_PUBLIC_API_BASE_URL": "/api",
            "SANDBOX_ALLOW_LIVE_EXECUTION": str(answers.sandbox_live_execution).lower(),
            "FEDERATION_ENABLED": str(answers.federation_enabled).lower(),
            "FEDERATION_CLUSTER_NAME": answers.federation_cluster_name,
            "FEDERATION_REGION": answers.federation_region,
            "FEDERATION_PEER_ENDPOINTS": ",".join(answers.federation_peers),
        }
        managed.update(local_secrets)
        lines = [line for line in base_lines if not any(line.startswith(f"{key}=") for key in managed)]
        lines.extend(f"{key}={value}" for key, value in managed.items())
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._secure_local_env_file(env_path)
        return env_path

    def _secure_local_env_file(self, env_path: Path) -> None:
        """Apply best-effort owner-only permissions to installer-managed env files."""

        try:
            if os.name == "nt":
                self._secure_local_env_file_windows(env_path)
            else:
                env_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError as exc:
            print(f"==> Warning: unable to tighten permissions on {env_path}: {exc}")  # noqa: T201

    def _secure_local_env_file_windows(self, env_path: Path) -> None:
        if shutil.which("icacls") is None:
            os.chmod(env_path, stat.S_IREAD | stat.S_IWRITE)
            return
        current_user = getpass.getuser()
        commands = [
            ["icacls", str(env_path), "/inheritance:r"],
            ["icacls", str(env_path), "/grant:r", f"{current_user}:(R,W)"],
        ]
        for command in commands:
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            if completed.returncode != 0:
                msg = completed.stderr.strip() or completed.stdout.strip() or "icacls failed"
                raise OSError(msg)

    def _write_generated_helm_values(self, answers: InstallerAnswers) -> Path:
        output_path = self.state_dir / "values.generated.yaml"
        content = [
            f"ingress:\n  enabled: true\n  host: {answers.enterprise_ingress_host}",
            f"federation:\n  enabled: {str(answers.federation_enabled).lower()}\n  clusterName: {answers.federation_cluster_name}\n  region: {answers.federation_region}",
        ]
        if answers.federation_peers:
            peers = "\n".join(f"    - {peer}" for peer in answers.federation_peers)
            content.append(f"  peers:\n{peers}")
        output_path.write_text("\n".join(content) + "\n", encoding="utf-8")
        return output_path

    def _maybe_launch_local(self, answers: InstallerAnswers) -> None:
        if not answers.enable_local_launch:
            return
        env = os.environ.copy()
        env["COMPOSE_PROJECT_NAME"] = f"frontier-{answers.local_hostname}"
        env["LOCAL_STACK_HOST"] = f"{answers.local_hostname}.localhost"
        env["SANDBOX_ALLOW_LIVE_EXECUTION"] = str(answers.sandbox_live_execution).lower()
        subprocess.run(["docker", "compose", "--env-file", str(self.state_dir / "local.env"), "up", "-d"], cwd=self.repo_root, env=env, check=True)

    def _print_local_access(self, answers: InstallerAnswers) -> None:
        url = f"http://{answers.local_hostname}.localhost"
        print(f"==> Local access URL: {url}")  # noqa: T201
        print("==> If the local gateway container is running, this hostname should route to the Frontier frontend and proxy /api requests to the orchestrator.")  # noqa: T201

    def _print_enterprise_access(self, answers: InstallerAnswers) -> None:
        values_file = self.state_dir / "values.generated.yaml"
        print("==> Enterprise Helm command:")  # noqa: T201
        print(  # noqa: T201
            f"helm upgrade --install lattix ./helm/lattix-frontier -n {answers.enterprise_namespace} --create-namespace -f {values_file}"
        )
        if answers.federation_enabled:
            print("==> Federation enabled. Configure secure inter-cluster connectivity for the listed peers.")  # noqa: T201


def main() -> None:
    """Console-script entrypoint."""

    installer = FrontierInstaller()
    raise SystemExit(installer.run())


if __name__ == "__main__":
    main()
