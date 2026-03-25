from __future__ import annotations

import builtins
from dataclasses import dataclass, field
import os
from pathlib import Path
import getpass
import re
import secrets
import shutil
import socket
import subprocess
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit


@dataclass(frozen=True)
class DiagnosticResult:
    name: str
    ok: bool
    message: str


def hostname_prefix_valid(prefix: str) -> DiagnosticResult:
    normalized = str(prefix).strip()
    ok = bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", normalized))
    return DiagnosticResult("hostname-prefix", ok, "valid" if ok else "Use lowercase letters, numbers, and hyphens only")


def writable_directory(path: Path) -> DiagnosticResult:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        return DiagnosticResult("writable-directory", False, str(exc))
    return DiagnosticResult("writable-directory", True, "writable")


def port_available(port: int) -> DiagnosticResult:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with sock:
            sock.bind(("127.0.0.1", port))
    except OSError as exc:
        return DiagnosticResult(f"port:{port}", False, str(exc))
    return DiagnosticResult(f"port:{port}", True, "available")


def _normalize_absolute_http_url(value: str, *, setting_name: str, allow_query: bool = False) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if any(ord(char) < 32 for char in raw):
        raise ValueError(f"{setting_name} contains invalid control characters")

    parsed = urlsplit(raw)
    scheme = str(parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"{setting_name} must use http or https")
    if not parsed.netloc or not parsed.hostname:
        raise ValueError(f"{setting_name} must be an absolute URL")
    if parsed.username or parsed.password:
        raise ValueError(f"{setting_name} must not embed credentials")
    if parsed.fragment:
        raise ValueError(f"{setting_name} must not include a fragment")
    if not allow_query and parsed.query:
        raise ValueError(f"{setting_name} must not include query parameters")
    if "\\" in parsed.netloc or "\\" in parsed.path:
        raise ValueError(f"{setting_name} contains invalid path separators")

    return urlunsplit((scheme, parsed.netloc, parsed.path or "", parsed.query if allow_query else "", ""))


def docker_daemon_available() -> DiagnosticResult:
    if shutil.which("docker") is None:
        return DiagnosticResult("docker-daemon", False, "Docker is not installed or not on PATH")
    result = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if result.returncode != 0:
        return DiagnosticResult("docker-daemon", False, "Start Docker Desktop or the docker service before continuing")
    return DiagnosticResult("docker-daemon", True, "available")


def docker_compose_available() -> DiagnosticResult:
    if shutil.which("docker") is None:
        return DiagnosticResult("docker-compose", False, "Docker is not installed or not on PATH")
    result = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True)
    if result.returncode != 0:
        return DiagnosticResult("docker-compose", False, "Docker Compose v2 plugin is not available")
    return DiagnosticResult("docker-compose", True, "available")


@dataclass(frozen=True)
class PrerequisiteDefinition:
    key: str
    display_name: str
    check_name: str
    install_commands: tuple[tuple[str, ...], ...] = ()
    manual_steps: tuple[str, ...] = ()


@dataclass(frozen=True)
class MissingPrerequisite:
    definition: PrerequisiteDefinition
    result: DiagnosticResult


@dataclass
class InstallerAnswers:
    installation_root: str
    deployment_mode: str = "local"
    local_hostname: str = "frontier"
    local_auth_provider: str = "oidc"
    oidc_provider_template: str = "casdoor"
    bootstrap_admin_username: str = ""
    bootstrap_admin_email: str = ""
    bootstrap_admin_subject: str = ""
    openai_api_key: str = ""
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    oidc_client_id: str = ""
    oidc_authorization_url: str = ""
    oidc_token_url: str = ""
    oidc_signin_url: str = ""
    oidc_signup_url: str = ""
    oidc_scopes: list[str] = field(default_factory=lambda: ["openid", "profile", "email"])
    federation_enabled: bool = False
    federation_cluster_name: str = ""
    federation_region: str = ""
    federation_peers: list[str] = field(default_factory=list)


class FrontierInstaller:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    @staticmethod
    def _normalize_auth_provider(value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized == "casdoor":
            return "oidc"
        if normalized in {"oidc", "shared-token"}:
            return normalized
        return "oidc"

    @staticmethod
    def _normalize_oidc_provider_template(value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"", "casdoor", "external", "generic", "custom"}:
            return "external" if normalized in {"", "generic", "custom"} else normalized
        return "external"

    @staticmethod
    def _normalized_oidc_provider_name(answers: InstallerAnswers) -> str:
        auth_provider = FrontierInstaller._normalize_auth_provider(answers.local_auth_provider)
        if auth_provider != "oidc":
            return ""
        if str(answers.local_auth_provider or "").strip().lower() == "casdoor":
            return "casdoor"
        template = FrontierInstaller._normalize_oidc_provider_template(answers.oidc_provider_template)
        return "casdoor" if template == "casdoor" else "oidc"

    @classmethod
    def _resolved_oidc_settings(cls, answers: InstallerAnswers) -> dict[str, str]:
        provider_name = cls._normalized_oidc_provider_name(answers)
        if provider_name == "casdoor":
            issuer = _normalize_absolute_http_url(
                answers.oidc_issuer or "http://casdoor.localhost",
                setting_name="FRONTIER_AUTH_OIDC_ISSUER",
            )
            authorization_url = _normalize_absolute_http_url(
                answers.oidc_authorization_url or f"{issuer}/login/oauth/authorize",
                setting_name="FRONTIER_AUTH_OIDC_AUTHORIZATION_URL",
                allow_query=True,
            )
            return {
                "provider": "casdoor",
                "issuer": issuer,
                "audience": answers.oidc_audience or "frontier-ui",
                "jwks_url": _normalize_absolute_http_url(
                    answers.oidc_jwks_url or f"{issuer}/.well-known/jwks.json",
                    setting_name="FRONTIER_AUTH_OIDC_JWKS_URL",
                ),
                "client_id": answers.oidc_client_id or "frontier-web",
                "authorization_url": authorization_url,
                "token_url": _normalize_absolute_http_url(
                    answers.oidc_token_url or f"{issuer}/api/login/oauth/access_token",
                    setting_name="FRONTIER_AUTH_OIDC_TOKEN_URL",
                ),
                "signin_url": _normalize_absolute_http_url(
                    answers.oidc_signin_url or authorization_url,
                    setting_name="FRONTIER_AUTH_OIDC_SIGNIN_URL",
                    allow_query=True,
                ),
                "signup_url": _normalize_absolute_http_url(
                    answers.oidc_signup_url or authorization_url,
                    setting_name="FRONTIER_AUTH_OIDC_SIGNUP_URL",
                    allow_query=True,
                ),
                "scopes": cls._oidc_scopes_value(answers),
            }
        authorization_url = _normalize_absolute_http_url(
            answers.oidc_authorization_url,
            setting_name="FRONTIER_AUTH_OIDC_AUTHORIZATION_URL",
            allow_query=True,
        )
        return {
            "provider": provider_name,
            "issuer": _normalize_absolute_http_url(answers.oidc_issuer, setting_name="FRONTIER_AUTH_OIDC_ISSUER"),
            "audience": answers.oidc_audience,
            "jwks_url": _normalize_absolute_http_url(answers.oidc_jwks_url, setting_name="FRONTIER_AUTH_OIDC_JWKS_URL"),
            "client_id": answers.oidc_client_id,
            "authorization_url": authorization_url,
            "token_url": _normalize_absolute_http_url(answers.oidc_token_url, setting_name="FRONTIER_AUTH_OIDC_TOKEN_URL"),
            "signin_url": _normalize_absolute_http_url(
                answers.oidc_signin_url or authorization_url,
                setting_name="FRONTIER_AUTH_OIDC_SIGNIN_URL",
                allow_query=True,
            ),
            "signup_url": _normalize_absolute_http_url(
                answers.oidc_signup_url or authorization_url,
                setting_name="FRONTIER_AUTH_OIDC_SIGNUP_URL",
                allow_query=True,
            ),
            "scopes": cls._oidc_scopes_value(answers),
        }

    @staticmethod
    def _oidc_scopes_value(answers: InstallerAnswers) -> str:
        scopes = [str(scope).strip() for scope in answers.oidc_scopes if str(scope).strip()]
        return " ".join(scopes) if scopes else "openid profile email"

    @staticmethod
    def _resolved_bootstrap_admin_identity(answers: InstallerAnswers) -> dict[str, str]:
        username = str(answers.bootstrap_admin_username or "").strip() or "frontier-admin"
        email = str(answers.bootstrap_admin_email or "").strip() or f"admin@{answers.local_hostname}.localhost"
        subject = str(answers.bootstrap_admin_subject or "").strip() or username
        references: list[str] = []
        for candidate in [username, email, subject]:
            normalized = str(candidate or "").strip()
            if normalized and normalized not in references:
                references.append(normalized)
        return {
            "username": username,
            "email": email,
            "subject": subject,
            "actor_list": ",".join(references),
        }

    def _write_env_file(self, answers: InstallerAnswers, secrets_map: dict[str, str]) -> Path:
        generated_dir = self.repo_root / ".installer"
        generated_dir.mkdir(parents=True, exist_ok=True)
        env_path = generated_dir / "local-secure.env"
        base_lines: list[str] = []
        example_path = self.repo_root / ".env.example"
        if example_path.exists():
            base_lines = [line.rstrip("\n") for line in example_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        generated_lines = [
            *base_lines,
            f"LOCAL_STACK_HOST={answers.local_hostname}.localhost",
            "CASDOOR_LOCAL_HOST=casdoor.localhost",
            "CASDOOR_PUBLIC_URL=http://casdoor.localhost",
            "FRONTIER_RUNTIME_PROFILE=local-secure",
            "FRONTIER_SECURE_LOCAL_MODE=true",
            "FRONTIER_REQUIRE_AUTHENTICATED_REQUESTS=true",
            "FRONTIER_ALLOW_HEADER_ACTOR_AUTH=false",
            "NEXT_PUBLIC_API_BASE_URL=/api",
            f"FRONTEND_ORIGIN=http://{answers.local_hostname}.localhost",
            f"FRONTIER_AUTH_MODE={self._normalize_auth_provider(answers.local_auth_provider)}",
            "A2A_JWT_AUD=frontier-runtime",
            "A2A_TRUSTED_SUBJECTS=backend,research,code,review,coordinator",
            f"FEDERATION_ENABLED={'true' if answers.federation_enabled else 'false'}",
            f"FEDERATION_CLUSTER_NAME={answers.federation_cluster_name}",
            f"FEDERATION_REGION={answers.federation_region}",
            f"FEDERATION_PEERS={','.join(answers.federation_peers)}",
        ]
        bootstrap_admin = self._resolved_bootstrap_admin_identity(answers)
        generated_lines.extend(
            [
                f"FRONTIER_BOOTSTRAP_ADMIN_USERNAME={bootstrap_admin['username']}",
                f"FRONTIER_BOOTSTRAP_ADMIN_EMAIL={bootstrap_admin['email']}",
                f"FRONTIER_BOOTSTRAP_ADMIN_SUBJECT={bootstrap_admin['subject']}",
                f"FRONTIER_ADMIN_ACTORS={bootstrap_admin['actor_list']}",
                f"FRONTIER_BUILDER_ACTORS={bootstrap_admin['actor_list']}",
                f"CASDOOR_BOOTSTRAP_ADMIN_USERNAME={bootstrap_admin['username']}",
                f"CASDOOR_BOOTSTRAP_ADMIN_EMAIL={bootstrap_admin['email']}",
            ]
        )
        if self._normalize_auth_provider(answers.local_auth_provider) == "oidc":
            oidc_settings = self._resolved_oidc_settings(answers)
            generated_lines.extend(
                [
                    "NEXT_PUBLIC_FRONTIER_ACTOR=",
                    "FRONTIER_API_BEARER_TOKEN=",
                    f"FRONTIER_AUTH_OIDC_PROVIDER={oidc_settings['provider']}",
                    f"FRONTIER_AUTH_OIDC_ISSUER={oidc_settings['issuer']}",
                    f"FRONTIER_AUTH_OIDC_AUDIENCE={oidc_settings['audience']}",
                    f"FRONTIER_AUTH_OIDC_JWKS_URL={oidc_settings['jwks_url']}",
                    f"FRONTIER_AUTH_OIDC_CLIENT_ID={oidc_settings['client_id']}",
                    f"FRONTIER_AUTH_OIDC_AUTHORIZATION_URL={oidc_settings['authorization_url']}",
                    f"FRONTIER_AUTH_OIDC_TOKEN_URL={oidc_settings['token_url']}",
                    f"FRONTIER_AUTH_OIDC_SIGNIN_URL={oidc_settings['signin_url']}",
                    f"FRONTIER_AUTH_OIDC_SIGNUP_URL={oidc_settings['signup_url']}",
                    f"FRONTIER_AUTH_OIDC_SCOPES={oidc_settings['scopes']}",
                ]
            )
        else:
            shared_token = secrets_map.get("FRONTIER_API_BEARER_TOKEN", "")
            generated_lines.extend(
                [
                    f"FRONTIER_API_BEARER_TOKEN={shared_token}",
                    "NEXT_PUBLIC_FRONTIER_ACTOR=",
                    "FRONTIER_AUTH_OIDC_PROVIDER=",
                    "FRONTIER_AUTH_OIDC_ISSUER=",
                    "FRONTIER_AUTH_OIDC_AUDIENCE=",
                    "FRONTIER_AUTH_OIDC_JWKS_URL=",
                    "FRONTIER_AUTH_OIDC_CLIENT_ID=",
                    "FRONTIER_AUTH_OIDC_AUTHORIZATION_URL=",
                    "FRONTIER_AUTH_OIDC_TOKEN_URL=",
                    "FRONTIER_AUTH_OIDC_SIGNIN_URL=",
                    "FRONTIER_AUTH_OIDC_SIGNUP_URL=",
                    "FRONTIER_AUTH_OIDC_SCOPES=",
                ]
            )
        postgres_password = secrets_map.get("POSTGRES_PASSWORD", "")
        postgres_db = os.getenv("POSTGRES_DB", "frontier")
        postgres_user = os.getenv("POSTGRES_USER", "frontier")
        neo4j_password = secrets_map.get("NEO4J_PASSWORD", "")
        generated_lines.extend(
            [
                f"POSTGRES_USER={postgres_user}",
                f"POSTGRES_PASSWORD={postgres_password}",
                f"POSTGRES_DB={postgres_db}",
                f"POSTGRES_DSN=postgresql://{postgres_user}:{postgres_password}@postgres:5432/{postgres_db}",
                "NEO4J_USERNAME=neo4j",
                f"NEO4J_PASSWORD={neo4j_password}",
            ]
        )
        for key, value in secrets_map.items():
            if key in {"FRONTIER_API_BEARER_TOKEN", "POSTGRES_PASSWORD", "NEO4J_PASSWORD"}:
                continue
            generated_lines.append(f"{key}={value}")
        env_path.write_text("\n".join(generated_lines) + "\n", encoding="utf-8")
        return env_path

    def _collect_local_secrets(self, answers: InstallerAnswers) -> dict[str, str]:
        if answers.deployment_mode == "enterprise":
            return {}
        a2a_secret = getpass.getpass("A2A_JWT_SECRET (leave blank to generate): ").strip() or secrets.token_urlsafe(32)
        postgres_password = getpass.getpass("POSTGRES_PASSWORD (leave blank to generate): ").strip() or secrets.token_urlsafe(24)
        neo4j_password = getpass.getpass("NEO4J_PASSWORD (leave blank to generate): ").strip() or secrets.token_urlsafe(24)
        secrets_map = {
            "A2A_JWT_SECRET": a2a_secret,
            "POSTGRES_PASSWORD": postgres_password,
            "NEO4J_PASSWORD": neo4j_password,
        }
        if self._normalize_auth_provider(answers.local_auth_provider) == "shared-token":
            provided_bearer = getpass.getpass("FRONTIER_API_BEARER_TOKEN (leave blank to generate): ").strip()
            secrets_map["FRONTIER_API_BEARER_TOKEN"] = provided_bearer or secrets.token_urlsafe(32)
        return secrets_map

    def _write_generated_helm_values(self, answers: InstallerAnswers) -> Path:
        output = self.repo_root / ".installer" / "generated-values.yaml"
        output.parent.mkdir(parents=True, exist_ok=True)
        peer_lines = "\n".join(f"  - {peer}" for peer in answers.federation_peers)
        output.write_text(
            "\n".join(
                [
                    f"clusterName: {answers.federation_cluster_name}",
                    f"region: {answers.federation_region}",
                    "peers:",
                    peer_lines or "  []",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return output

    def _ask_yes_no(self, prompt: str, default: bool) -> bool:
        suffix = "[Y/n]" if default else "[y/N]"
        while True:
            response = builtins.input(f"{prompt} {suffix} ").strip().lower()
            if not response:
                return default
            if response in {"y", "yes"}:
                return True
            if response in {"n", "no"}:
                return False
            print("Please answer yes or no.")  # noqa: T201

    def _run_install_command(self, command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, capture_output=True, text=True)

    def _run_prerequisite_check(self, definition: PrerequisiteDefinition) -> DiagnosticResult:
        check_name = str(definition.check_name or "").strip()
        if check_name == "docker-daemon":
            return docker_daemon_available()
        if check_name == "docker-compose":
            return docker_compose_available()
        if check_name.startswith("command:"):
            command = check_name.split(":", 1)[1].strip()
            if not command:
                return DiagnosticResult(check_name, False, "missing command name")
            if shutil.which(command) is None:
                return DiagnosticResult(check_name, False, f"{command} is missing from PATH")
            return DiagnosticResult(check_name, True, "available")
        return DiagnosticResult(check_name or definition.key, False, f"Unsupported prerequisite check: {check_name or definition.key}")

    def _attempt_missing_prerequisite_installs(
        self,
        missing: Iterable[MissingPrerequisite],
    ) -> list[MissingPrerequisite]:
        unresolved: list[MissingPrerequisite] = []
        for item in missing:
            install_succeeded = False
            failure_message = item.result.message
            for command in item.definition.install_commands:
                result = self._run_install_command(command)
                if result.returncode == 0:
                    recheck = self._run_prerequisite_check(item.definition)
                    if recheck.ok:
                        install_succeeded = True
                        break
                    failure_message = recheck.message
                    continue
                failure_message = result.stderr or result.stdout or failure_message
            if not install_succeeded:
                unresolved.append(
                    MissingPrerequisite(
                        definition=item.definition,
                        result=DiagnosticResult(item.definition.check_name, False, failure_message),
                    )
                )
        return unresolved

    def _resolve_missing_prerequisites(self, missing: list[MissingPrerequisite], intro: str) -> None:
        if not missing:
            return
        if self._ask_yes_no(intro, True):
            unresolved = self._attempt_missing_prerequisite_installs(missing)
            if not unresolved:
                return
            missing = unresolved
        lines = ["Outstanding prerequisites:"]
        for item in missing:
            lines.append(f"- {item.definition.display_name}: {item.result.message}")
            for command in item.definition.install_commands:
                lines.append("  " + " ".join(command))
            for step in item.definition.manual_steps:
                lines.append("  " + step)
        raise SystemExit("\n".join(lines))
