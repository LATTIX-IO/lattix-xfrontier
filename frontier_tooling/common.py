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
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_DIR = REPO_ROOT / ".installer"
INSTALLER_ENV_PATH = INSTALLER_DIR / "local.env"
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


def ensure_compose_env_file() -> Path:
    env_map: OrderedDict[str, str] = OrderedDict()
    for source in (REPO_ROOT / ".env.example", REPO_ROOT / ".env", INSTALLER_ENV_PATH):
        for key, value in _read_env_map(source).items():
            env_map[key] = value

    env_map.setdefault("A2A_JWT_SECRET", _random_secret())
    env_map.setdefault("A2A_JWT_ALG", "HS256")
    env_map.setdefault("A2A_JWT_ISS", "lattix-frontier")
    env_map.setdefault("A2A_JWT_AUD", "agents")
    env_map.setdefault("A2A_TRUSTED_SUBJECTS", "backend,research,code,review,coordinator")
    env_map.setdefault("NEXT_PUBLIC_API_BASE_URL", "/api")
    env_map.setdefault("FRONTIER_LOCAL_API_BASE_URL", "http://localhost:8000")
    env_map.setdefault("LOCAL_STACK_HOST", "frontier.localhost")
    return _write_env_map(INSTALLER_ENV_PATH, env_map)


def compose_prefix(*, local: bool) -> list[str]:
    env_path = ensure_compose_env_file()
    base = ["docker", "compose", "--env-file", str(env_path)]
    if local:
        base.extend(["-f", "docker-compose.local.yml"])
    return base


def run_command(args: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=str(cwd or REPO_ROOT), check=True)


def request_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None, timeout: int = 10) -> Any:
    headers = {"Accept": "application/json"}
    bearer = str(os.getenv("FRONTIER_API_BEARER_TOKEN", "") or "").strip()
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, method=method, headers=headers)
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        raw = response.read().decode("utf-8")
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
