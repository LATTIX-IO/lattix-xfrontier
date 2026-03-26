from __future__ import annotations

import base64
import json
import os
import platform
import secrets
import site
import socket
import subprocess
import sys
import sysconfig
from collections import OrderedDict
from pathlib import Path
from typing import Any
from collections.abc import Mapping

from urllib.parse import urlparse

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FRONTIER_APP_HOME_ENV = "FRONTIER_APP_HOME"
DEFAULT_LOCAL_STACK_HOST = "xfrontier.local"
DEFAULT_ARCHIVE_URL = "https://github.com/LATTIX-IO/lattix-xfrontier/archive/refs/heads/main.zip"


def _normalized_gateway_bind_host(value: str | None) -> str:
    host = str(value or "").strip()
    if not host or host == "0.0.0.0":
        return "127.0.0.1"
    return host


def _default_secure_local_api_base_url(env_map: OrderedDict[str, str]) -> str:
    host = _normalized_gateway_bind_host(env_map.get("LOCAL_GATEWAY_BIND_HOST"))
    port = str(env_map.get("LOCAL_GATEWAY_HTTP_PORT") or "80").strip() or "80"
    authority = host if port == "80" else f"{host}:{port}"
    return f"http://{authority}/api"


def source_repo_root() -> Path:
    return PACKAGE_ROOT


def default_app_home() -> Path:
    home = Path.home()
    system = platform.system().lower()
    if system == "windows":
        base = Path(os.getenv("LOCALAPPDATA") or (home / "AppData" / "Local"))
        return base / "Lattix" / "xFrontier"
    if system == "darwin":
        return home / "Library" / "Application Support" / "Lattix" / "xFrontier"
    xdg_data_home = str(os.getenv("XDG_DATA_HOME") or "").strip()
    if xdg_data_home:
        return Path(xdg_data_home) / "lattix" / "xfrontier"
    return home / ".local" / "share" / "lattix" / "xfrontier"


def _looks_like_repo_root(candidate: Path) -> bool:
    return all(
        [
            (candidate / "pyproject.toml").exists(),
            (candidate / "frontier_tooling").exists(),
            (candidate / "docker-compose.yml").exists(),
        ]
    )


def repo_root() -> Path:
    configured = str(os.getenv(FRONTIER_APP_HOME_ENV) or "").strip()
    if configured:
        candidate = Path(configured).expanduser().resolve(strict=False)
        if _looks_like_repo_root(candidate):
            return candidate
    for candidate in (PACKAGE_ROOT, default_app_home()):
        resolved = candidate.expanduser().resolve(strict=False)
        if _looks_like_repo_root(resolved):
            return resolved
    return PACKAGE_ROOT


def python_executable() -> str:
    return sys.executable


def user_scripts_dir() -> Path:
    scheme = sysconfig.get_preferred_scheme("user")
    scripts_path = sysconfig.get_path("scripts", scheme=scheme)
    if scripts_path:
        return Path(scripts_path)
    return Path(site.getuserbase()) / ("Scripts" if os.name == "nt" else "bin")


def python_scripts_dir() -> Path:
    scripts_path = sysconfig.get_path("scripts")
    if scripts_path:
        return Path(scripts_path)
    return Path(sys.executable).resolve().parent


def cli_executable(command_name: str = "lattix", *, scripts_dir: Path | None = None) -> Path:
    resolved_scripts_dir = scripts_dir or user_scripts_dir()
    suffix = ".exe" if os.name == "nt" else ""
    return resolved_scripts_dir / f"{command_name}{suffix}"


def installer_dir(*, root: Path | None = None) -> Path:
    return (root or repo_root()) / ".installer"


def secure_installer_env_path(*, root: Path | None = None) -> Path:
    return installer_dir(root=root) / "local-secure.env"


def lightweight_installer_env_path(*, root: Path | None = None) -> Path:
    return installer_dir(root=root) / "local-lightweight.env"


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


def _installer_env_path(*, local_profile: bool, root: Path | None = None) -> Path:
    return lightweight_installer_env_path(root=root) if local_profile else secure_installer_env_path(root=root)


def installer_artifact_paths(*, root: Path | None = None) -> list[Path]:
    base = installer_dir(root=root)
    return [
        secure_installer_env_path(root=root),
        lightweight_installer_env_path(root=root),
        base / "local.env",
        base / "generated-values.yaml",
    ]


def ensure_compose_env_file(*, local_profile: bool = False, root: Path | None = None) -> Path:
    env_map: OrderedDict[str, str] = OrderedDict()
    resolved_root = root or repo_root()
    installer_env_path = _installer_env_path(local_profile=local_profile, root=resolved_root)
    for source in (resolved_root / ".env.example", resolved_root / ".env", installer_env_path):
        for key, value in _read_env_map(source).items():
            env_map[key] = value

    if not str(env_map.get("A2A_JWT_SECRET") or "").strip():
        env_map["A2A_JWT_SECRET"] = _random_secret()
    env_map.setdefault("A2A_JWT_ALG", "HS256")
    env_map.setdefault("A2A_JWT_ISS", "lattix-frontier")
    env_map["A2A_JWT_AUD"] = _normalize_a2a_audience(env_map.get("A2A_JWT_AUD"))
    env_map["A2A_TRUSTED_SUBJECTS"] = "backend,research,code,review,coordinator"
    env_map.setdefault("LOCAL_STACK_HOST", DEFAULT_LOCAL_STACK_HOST)
    if local_profile:
        env_map["FRONTIER_RUNTIME_PROFILE"] = "local-lightweight"
        env_map["NEXT_PUBLIC_API_BASE_URL"] = "http://localhost:8000"
        env_map["FRONTEND_ORIGIN"] = "http://localhost:3000"
        env_map["FRONTIER_LOCAL_API_BASE_URL"] = "http://localhost:8000"
    else:
        env_map["FRONTIER_RUNTIME_PROFILE"] = "local-secure"
        env_map["FRONTIER_LOCAL_BOOTSTRAP_AUTHENTICATED_OPERATOR"] = "true"
        env_map["NEXT_PUBLIC_API_BASE_URL"] = "/api"
        env_map["FRONTEND_ORIGIN"] = f"http://{env_map['LOCAL_STACK_HOST']}"
        secure_api_base = _default_secure_local_api_base_url(env_map)
        configured_api_base = str(env_map.get("FRONTIER_LOCAL_API_BASE_URL") or "").strip()
        if not configured_api_base or configured_api_base == "http://localhost:8000":
            env_map["FRONTIER_LOCAL_API_BASE_URL"] = secure_api_base
    return _write_env_map(installer_env_path, env_map)


def configured_local_api_base_url(*, root: Path | None = None) -> str:
    resolved_root = root or repo_root()
    secure_env_path = secure_installer_env_path(root=resolved_root)
    lightweight_env_path = lightweight_installer_env_path(root=resolved_root)

    if secure_env_path.exists() or not lightweight_env_path.exists():
        env_map = _read_env_map(ensure_compose_env_file(local_profile=False, root=resolved_root))
        default_base = _default_secure_local_api_base_url(env_map)
    else:
        env_map = _read_env_map(ensure_compose_env_file(local_profile=True, root=resolved_root))
        default_base = "http://localhost:8000"

    configured = str(env_map.get("FRONTIER_LOCAL_API_BASE_URL") or "").strip()
    return (configured or default_base).rstrip("/")


def configured_local_api_headers(*, root: Path | None = None) -> dict[str, str]:
    resolved_root = root or repo_root()
    secure_env_path = secure_installer_env_path(root=resolved_root)
    lightweight_env_path = lightweight_installer_env_path(root=resolved_root)

    if secure_env_path.exists() or not lightweight_env_path.exists():
        env_map = _read_env_map(ensure_compose_env_file(local_profile=False, root=resolved_root))
        host = str(env_map.get("LOCAL_STACK_HOST") or "").strip()
        return {"Host": host} if host else {}
    return {}


def configured_local_api_url(path: str, *, root: Path | None = None) -> str:
    return f"{configured_local_api_base_url(root=root)}/{path.lstrip('/')}"


def compose_prefix(*, local: bool, root: Path | None = None) -> list[str]:
    env_path = ensure_compose_env_file(local_profile=local, root=root)
    base = ["docker", "compose", "--env-file", str(env_path)]
    if local:
        base.extend(["-f", "docker-compose.local.yml"])
    return base


def existing_compose_prefix(*, local: bool, root: Path | None = None) -> list[str] | None:
    env_path = _installer_env_path(local_profile=local, root=root)
    if not env_path.exists():
        return None
    base = ["docker", "compose", "--env-file", str(env_path)]
    if local:
        base.extend(["-f", "docker-compose.local.yml"])
    return base


def remove_installer_env_files(*, root: Path | None = None) -> list[Path]:
    removed: list[Path] = []
    for path in (secure_installer_env_path(root=root), lightweight_installer_env_path(root=root)):
        if path.exists():
            path.unlink()
            removed.append(path)
    return removed


def remove_installer_artifacts(*, root: Path | None = None) -> list[Path]:
    removed: list[Path] = []
    seen: set[Path] = set()
    for path in installer_artifact_paths(root=root):
        if path in seen:
            continue
        seen.add(path)
        if path.exists():
            path.unlink()
            removed.append(path)
    installer_root = installer_dir(root=root)
    if installer_root.exists():
        try:
            installer_root.rmdir()
        except OSError:
            pass
    return removed


def run_command(
    args: list[str], *, cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(args, cwd=str(cwd or repo_root()), check=check, env=env)


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


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: Mapping[str, Any] | None = None,
    timeout: int = 10,
    extra_headers: dict[str, str] | None = None,
) -> Any:
    import httpx

    headers = {"Accept": "application/json"}
    if extra_headers:
        headers.update({key: value for key, value in extra_headers.items() if str(value or "").strip()})
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


def _detect_primary_ipv4() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            address = str(sock.getsockname()[0]).strip()
            if address:
                return address
    except OSError:
        pass
    try:
        address = str(socket.gethostbyname(socket.gethostname())).strip()
    except OSError:
        return None
    return address or None


def portal_urls(*, root: Path | None = None) -> list[str]:
    env_map = _read_env_map(ensure_compose_env_file(local_profile=False, root=root))
    host = str(env_map.get("LOCAL_STACK_HOST") or DEFAULT_LOCAL_STACK_HOST).strip() or DEFAULT_LOCAL_STACK_HOST
    urls = [f"http://{host}", "http://127.0.0.1"]
    lan_ip = _detect_primary_ipv4()
    if lan_ip and lan_ip != "127.0.0.1":
        urls.append(f"http://{lan_ip}")
    deduped: list[str] = []
    for url in urls:
        if url not in deduped:
            deduped.append(url)
    return deduped


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
    resolved_root = repo_root()
    roots: list[Path] = [(resolved_root / "examples" / "agents").resolve()]
    if configured:
        configured_path = Path(configured)
        if not configured_path.is_absolute():
            configured_path = (resolved_root / configured_path).resolve()
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
    local_opa = repo_root() / ".tools" / "opa" / ("opa.exe" if os.name == "nt" else "opa")
    if local_opa.exists():
        return str(local_opa)
    return "opa"
