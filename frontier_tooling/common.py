from __future__ import annotations

import base64
import json
import os
import platform
import secrets
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_DIR = REPO_ROOT / ".installer"
SECURE_INSTALLER_ENV_PATH = INSTALLER_DIR / "local-secure.env"
LIGHTWEIGHT_INSTALLER_ENV_PATH = INSTALLER_DIR / "local-lightweight.env"
DEFAULT_ARCHIVE_URL = "https://github.com/LATTIX-IO/lattix-xfrontier/archive/refs/heads/main.zip"


def repo_root() -> Path:
    return REPO_ROOT


def python_executable() -> str:
    return sys.executable


def _read_env_map(path: Path) -> OrderedDict[str, str]:
    env_map: OrderedDict[str, str] = OrderedDict()
    if not path.exists():
        return env_map
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_map[key] = value
    return env_map


def _write_env_map(path: Path, env_map: OrderedDict[str, str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(f"{key}={value}" for key, value in env_map.items()) + "\n"
    path.write_text(payload, encoding="utf-8")
    return path


def _random_secret() -> str:
    return base64.b64encode(secrets.token_bytes(48)).decode("ascii").rstrip("=")


def _normalize_a2a_audience(value: str | None) -> str:
    text = str(value or "").strip()
    if not text or text == "agents":
        return "frontier-runtime"
    return text


def _installer_env_path(*, local_profile: bool) -> Path:
    return LIGHTWEIGHT_INSTALLER_ENV_PATH if local_profile else SECURE_INSTALLER_ENV_PATH


def ensure_compose_env_file(*, local_profile: bool = False) -> Path:
    env_map: OrderedDict[str, str] = OrderedDict()
    installer_env_path = _installer_env_path(local_profile=local_profile)
    for source in (REPO_ROOT / ".env.example", REPO_ROOT / ".env", installer_env_path):
        for key, value in _read_env_map(source).items():
            env_map[key] = value

    if not str(env_map.get("A2A_JWT_SECRET") or "").strip():
        env_map["A2A_JWT_SECRET"] = _random_secret()
    env_map.setdefault("A2A_JWT_ALG", "HS256")
    env_map.setdefault("A2A_JWT_ISS", "lattix-frontier")
    env_map["A2A_JWT_AUD"] = _normalize_a2a_audience(env_map.get("A2A_JWT_AUD"))
    env_map["A2A_TRUSTED_SUBJECTS"] = "backend,research,code,review,coordinator"
    env_map.setdefault("LOCAL_STACK_HOST", "frontier.localhost")
    if local_profile:
        env_map["FRONTIER_RUNTIME_PROFILE"] = "local-lightweight"
        env_map["NEXT_PUBLIC_API_BASE_URL"] = "http://localhost:8000"
        env_map["FRONTEND_ORIGIN"] = "http://localhost:3000"
        env_map["FRONTIER_LOCAL_API_BASE_URL"] = "http://localhost:8000"
    else:
        env_map["FRONTIER_RUNTIME_PROFILE"] = "local-secure"
        env_map["NEXT_PUBLIC_API_BASE_URL"] = "/api"
        env_map["FRONTEND_ORIGIN"] = f"http://{env_map['LOCAL_STACK_HOST']}"
        env_map.setdefault("FRONTIER_LOCAL_API_BASE_URL", "http://localhost:8000")
    return _write_env_map(installer_env_path, env_map)


def compose_prefix(*, local: bool) -> list[str]:
    env_path = ensure_compose_env_file(local_profile=local)
    base = ["docker", "compose", "--env-file", str(env_path)]
    if local:
        base.extend(["-f", "docker-compose.local.yml"])
    return base


def existing_compose_prefix(*, local: bool) -> list[str] | None:
    env_path = _installer_env_path(local_profile=local)
    if not env_path.exists():
        return None
    base = ["docker", "compose", "--env-file", str(env_path)]
    if local:
        base.extend(["-f", "docker-compose.local.yml"])
    return base


def remove_installer_env_files() -> list[Path]:
    removed: list[Path] = []
    for path in (SECURE_INSTALLER_ENV_PATH, LIGHTWEIGHT_INSTALLER_ENV_PATH):
        if path.exists():
            path.unlink()
            removed.append(path)
    return removed


def run_command(
    args: list[str], *, cwd: Path | None = None, check: bool = True
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(args, cwd=str(cwd or REPO_ROOT), check=check)


def _validated_http_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are supported")
    if not parsed.hostname:
        raise ValueError("A host is required")
    if parsed.username or parsed.password:
        raise ValueError("Embedded URL credentials are not supported")
    if parsed.fragment:
        raise ValueError("URL fragments are not supported")
    return parsed.geturl()


def request_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None, timeout: int = 10) -> Any:
    import httpx

    headers = {"Accept": "application/json"}
    bearer = str(os.getenv("FRONTIER_API_BEARER_TOKEN", "") or "").strip()
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    response = httpx.request(
        method,
        _validated_http_url(url),
        content=data,
        headers=headers,
        timeout=float(timeout),
        follow_redirects=False,
    )
    response.raise_for_status()
    raw = response.text
    return json.loads(raw) if raw else None


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=False))  # noqa: T201


def detect_sandbox_backend() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "docker-desktop-vm"
    if system == "darwin":
        return "docker-desktop-vm"
    if system == "linux":
        return "docker"
    return "unknown"


def agent_asset_roots() -> list[Path]:
    configured = str(os.getenv("FRONTIER_AGENT_ASSETS_ROOT", "") or "").strip()
    roots: list[Path] = [(REPO_ROOT / "examples" / "agents").resolve()]
    if configured:
        configured_path = Path(configured)
        if not configured_path.is_absolute():
            configured_path = (REPO_ROOT / configured_path).resolve()
        roots.append(configured_path)
    deduped: list[Path] = []
    seen: set[str] = set()
    for item in roots:
        key = str(item)
        if key not in seen:
            deduped.append(item)
            seen.add(key)
    return deduped


def discover_agent_records() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for root in agent_asset_roots():
        if not root.exists() or not root.is_dir():
            continue
        for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            agent_id = child.name
            if agent_id in seen:
                continue
            records.append({
                "id": agent_id,
                "name": agent_id.replace("-", " ").title(),
                "path": str(child),
                "source": str(root),
            })
            seen.add(agent_id)
    return records


def resolve_opa_command() -> str:
    local_opa = REPO_ROOT / ".tools" / "opa" / ("opa.exe" if os.name == "nt" else "opa")
    if local_opa.exists():
        return str(local_opa)
    return "opa"
