from __future__ import annotations

import os
from pathlib import Path
import platform
import json
import shutil
import stat
import sys
import tempfile
import textwrap
import time
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
import http.cookiejar
from urllib.parse import urlsplit, urlunsplit

from frontier_runtime.install import FrontierInstaller, InstallerAnswers

from .common import (
    DEFAULT_ARCHIVE_URL,
    FRONTIER_APP_HOME_ENV,
    cli_executable,
    compose_prefix,
    default_app_home,
    ensure_compose_env_file,
    portal_urls,
    print_json,
    python_scripts_dir,
    python_executable,
    run_command,
    source_repo_root,
    user_scripts_dir,
)


CASDOOR_BOOTSTRAP_MAX_ATTEMPTS = 90
CASDOOR_BOOTSTRAP_RETRY_DELAY_SECONDS = 2


def bootstrap_url() -> str:
    return DEFAULT_ARCHIVE_URL


def _display_mode() -> str:
    configured = str(os.getenv("FRONTIER_INSTALLER_OUTPUT") or "").strip().lower()
    if configured in {"json", "tui"}:
        return configured
    return "tui" if sys.stdout.isatty() else "json"


def _friendly_install_mode(mode: str) -> str:
    return "Source checkout" if mode == "editable" else "Published install"


def _render_box(title: str, lines: list[str]) -> str:
    width = max(72, min(shutil.get_terminal_size(fallback=(100, 24)).columns, 120)) - 4
    wrapped_lines: list[str] = []
    for line in lines:
        if not line:
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(textwrap.wrap(line, width=width, replace_whitespace=False, drop_whitespace=False) or [""])
    content = [title, *wrapped_lines]
    top = f"╔{'═' * (width + 2)}╗"
    body = [f"║ {line.ljust(width)} ║" for line in content]
    bottom = f"╚{'═' * (width + 2)}╝"
    return "\n".join([top, *body, bottom])


def _render_install_summary(payload: dict[str, Any]) -> str:
    raw_path_info = payload.get("path")
    path_info: dict[str, Any] = raw_path_info if isinstance(raw_path_info, dict) else {}

    raw_urls = payload.get("urls")
    urls: list[str] = [str(item) for item in raw_urls] if isinstance(raw_urls, list) else []

    raw_next_steps = payload.get("next_steps")
    next_steps: list[str] = [str(item) for item in raw_next_steps] if isinstance(raw_next_steps, list) else []

    raw_bootstrap_login = payload.get("bootstrap_login")
    bootstrap_login: dict[str, Any] = raw_bootstrap_login if isinstance(raw_bootstrap_login, dict) else {}

    raw_path_locations = path_info.get("locations")
    path_locations: list[str] = [str(item) for item in raw_path_locations] if isinstance(raw_path_locations, list) else []

    lines = [
        f"Status      : {'Ready' if payload.get('installed') else 'Not installed'}",
        f"Mode        : {_friendly_install_mode(str(payload.get('install_mode') or 'unknown'))}",
        f"Isolation   : {payload.get('security_posture')}",
        f"Auth mode   : {payload.get('auth_mode')}",
        f"App home    : {payload.get('repo_root')}",
        f"Env file    : {payload.get('compose_env')}",
        f"CLI path    : {path_info.get('cli_path')}",
        f"Scripts dir : {path_info.get('scripts_dir')}",
        f"PATH update : {'Applied' if path_info.get('updated') else 'Already present'}",
    ]
    if path_locations:
        lines.append(f"PATH scope  : {', '.join(str(item) for item in path_locations)}")

    if bootstrap_login.get("username"):
        lines.append("")
        lines.append("Bootstrap login")
        lines.append(f"  User      : {bootstrap_login.get('username')}")
        lines.append(f"  Email     : {bootstrap_login.get('email')}")
        lines.append(f"  Name      : {bootstrap_login.get('display_name')}")
        if bootstrap_login.get("password_generated"):
            lines.append(f"  Password  : {bootstrap_login.get('password')}")
        else:
            lines.append("  Password  : Uses the password entered during install")

    lines.append("")
    lines.append("Portal URLs")
    for index, url in enumerate(urls, start=1):
        lines.append(f"  [{index}] {url}")

    lines.append("")
    lines.append("Next steps")
    for step in next_steps:
        lines.append(f"  • {step}")
    lines.append("  • If PATH was updated, open a new terminal before running `lattix` manually.")

    lines.append("")
    lines.append(f"Install src : {payload.get('bootstrap_url')}")
    return _render_box("Lattix xFrontier install complete", lines)


def _print_install_result(payload: dict[str, Any]) -> None:
    if _display_mode() == "json":
        print_json(payload)
        return
    print(_render_install_summary(payload))  # noqa: T201


def _install_mode(root: Path) -> str:
    return "editable" if (root / ".git").exists() else "wheel"


def _pip_install_args(root: Path) -> list[str]:
    args = [python_executable(), "-m", "pip", "install"]
    if _install_mode(root) == "editable":
        args.append("-e")
    else:
        args.append("--user")
    args.append(".[dev]")
    return args


def _scripts_dir_for_install_mode(mode: str) -> Path:
    return python_scripts_dir() if mode == "editable" else user_scripts_dir()


def _runtime_env(install_root: Path, mode: str) -> dict[str, str]:
    scripts_dir = _scripts_dir_for_install_mode(mode)
    current_path = str(os.getenv("PATH") or "")
    path_entries = [entry for entry in current_path.split(os.pathsep) if entry]
    if str(scripts_dir) not in path_entries:
        path_entries.insert(0, str(scripts_dir))
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(path_entries)
    env[FRONTIER_APP_HOME_ENV] = str(install_root)
    return env


def _interactive_install() -> bool:
    configured = str(os.getenv("FRONTIER_INSTALLER_INTERACTIVE") or "").strip().lower()
    if configured in {"0", "false", "no"}:
        return False
    if configured in {"1", "true", "yes"}:
        return True
    return sys.stdin.isatty() and sys.stdout.isatty()


def _best_effort_owner_only_permissions(path: Path) -> None:
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        return


def _collect_installer_answers(install_root: Path) -> InstallerAnswers:
    installer = FrontierInstaller(repo_root=install_root)
    return installer.collect_local_answers(installation_root=install_root, interactive=_interactive_install())


def _write_secure_installer_env(install_root: Path, answers: InstallerAnswers) -> Path:
    installer = FrontierInstaller(repo_root=install_root)
    secrets_map = installer._collect_local_secrets(answers)
    installer._write_generated_helm_values(answers)
    return installer._write_env_file(answers, secrets_map)


def _source_copy_ignore(directory: str, names: list[str]) -> set[str]:
    ignored = {".git", ".venv", ".pytest_cache", ".mypy_cache", "__pycache__", "node_modules"}
    if Path(directory).name == ".installer":
        ignored.update(names)
    return {name for name in names if name in ignored}


def _prepare_install_root(source_root: Path) -> Path:
    install_root = default_app_home().resolve(strict=False)
    install_root.parent.mkdir(parents=True, exist_ok=True)
    staging_parent = Path(tempfile.mkdtemp(prefix="frontier-app-home-", dir=str(install_root.parent)))
    staged_root = staging_parent / install_root.name
    try:
        shutil.copytree(source_root, staged_root, ignore=_source_copy_ignore)
        if install_root.exists():
            shutil.rmtree(install_root)
        staged_root.replace(install_root)
    finally:
        shutil.rmtree(staging_parent, ignore_errors=True)
    return install_root


def _append_path_once(current: str, addition: str) -> str:
    entries = [entry for entry in current.split(os.pathsep) if entry]
    lowered = {entry.casefold() for entry in entries}
    if addition.casefold() not in lowered:
        entries.append(addition)
    return os.pathsep.join(entries)


def _update_windows_user_path(scripts_dir: Path) -> tuple[bool, list[str]]:
    import ctypes
    import winreg

    ctypes_api: Any = ctypes
    winreg_api: Any = winreg
    modified = False
    with winreg_api.OpenKey(
        winreg_api.HKEY_CURRENT_USER,
        "Environment",
        0,
        winreg_api.KEY_READ | winreg_api.KEY_WRITE,
    ) as key:
        try:
            current_value, _ = winreg_api.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current_value = ""
        updated_value = _append_path_once(str(current_value or ""), str(scripts_dir))
        if updated_value != str(current_value or ""):
            winreg_api.SetValueEx(key, "Path", 0, winreg_api.REG_EXPAND_SZ, updated_value)
            modified = True
    if modified:
        ctypes_api.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, 0)
    return modified, ["HKCU\\Environment\\Path"]


def _shell_profile_targets() -> list[Path]:
    home = Path.home()
    shell = Path(str(os.getenv("SHELL") or "")).name.lower()
    system = platform.system().lower()
    if system == "darwin":
        if shell == "zsh":
            return [home / ".zprofile"]
        if shell == "bash":
            return [home / ".bash_profile"]
        return [home / ".profile"]
    if shell == "zsh":
        return [home / ".zshrc"]
    if shell == "bash":
        return [home / ".bashrc", home / ".profile"]
    return [home / ".profile"]


def _update_posix_user_path(scripts_dir: Path) -> tuple[bool, list[str]]:
    block = (
        "# >>> lattix-xfrontier >>>\n"
        f'export PATH="{scripts_dir}:$PATH"\n'
        "# <<< lattix-xfrontier <<<\n"
    )
    modified_files: list[str] = []
    for profile_path in _shell_profile_targets():
        existing = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""
        if str(scripts_dir) in existing:
            continue
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        newline = "" if not existing or existing.endswith("\n") else "\n"
        profile_path.write_text(f"{existing}{newline}{block}", encoding="utf-8")
        modified_files.append(str(profile_path))
    return bool(modified_files), modified_files


def _ensure_scripts_path(mode: str) -> dict[str, object]:
    scripts_dir = _scripts_dir_for_install_mode(mode)
    os.environ.update({"PATH": _append_path_once(str(os.getenv("PATH") or ""), str(scripts_dir))})
    if os.name == "nt":
        updated, locations = _update_windows_user_path(scripts_dir)
    else:
        updated, locations = _update_posix_user_path(scripts_dir)
    return {
        "scripts_dir": str(scripts_dir),
        "updated": updated,
        "locations": locations,
        "cli_path": str(cli_executable(scripts_dir=scripts_dir)),
    }


def _casdoor_bootstrap_identity_enabled(answers: InstallerAnswers) -> bool:
    if FrontierInstaller._normalize_auth_provider(answers.local_auth_provider) != "oidc":
        return False
    if FrontierInstaller._normalize_oidc_provider_template(answers.oidc_provider_template) != "casdoor":
        return False
    return bool(str(answers.bootstrap_login_username or "").strip() and str(answers.bootstrap_login_password or ""))


def _casdoor_bootstrap_endpoint(answers: InstallerAnswers) -> tuple[str, dict[str, str]]:
    issuer = FrontierInstaller._resolved_oidc_settings(answers)["issuer"]
    parsed = urlsplit(issuer)
    host = str(parsed.hostname or "").strip().lower()
    if host.endswith(".localhost") or host in {"localhost", "127.0.0.1", "::1"}:
        bind_host = str(os.getenv("LOCAL_GATEWAY_BIND_HOST") or "127.0.0.1").strip() or "127.0.0.1"
        port = str(os.getenv("LOCAL_GATEWAY_HTTP_PORT") or "80").strip() or "80"
        netloc = bind_host if port == "80" else f"{bind_host}:{port}"
        return urlunsplit(("http", netloc, "", "", "")), {"Host": parsed.netloc}
    return issuer.rstrip("/"), {}


def _urlopen_json(
    opener: urllib_request.OpenerDirector,
    url: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    request = urllib_request.Request(url, data=data, method=method)
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    with opener.open(request, timeout=10) as response:
        payload = response.read().decode("utf-8", errors="replace")
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return {"status": "error", "msg": payload.strip() or "non-json response", "data": None, "data2": None}
    return parsed if isinstance(parsed, dict) else {"status": "error", "msg": "unexpected response shape", "data": parsed, "data2": None}


def _casdoor_login_admin(opener: urllib_request.OpenerDirector, base_url: str, headers: dict[str, str]) -> None:
    login_url = (
        f"{base_url.rstrip('/')}"
        "/api/login?clientId=app-built-in&responseType=code&redirectUri=http://localhost"
        "&scope=openid%20profile%20email&state=frontier-bootstrap"
    )
    login_payload = urllib_parse.urlencode(
        {
            "application": "app-built-in",
            "organization": "built-in",
            "username": "built-in/admin",
            "password": "123",
        }
    ).encode("utf-8")
    _urlopen_json(
        opener,
        login_url,
        method="POST",
        data=login_payload,
        headers={
            **headers,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    account = _urlopen_json(
        opener,
        f"{base_url.rstrip('/')}/api/get-account",
        headers={**headers, "Accept": "application/json"},
    )
    raw_account_data = account.get("data")
    account_data: dict[str, Any] = raw_account_data if isinstance(raw_account_data, dict) else {}
    if account.get("status") != "ok" or account_data.get("owner") != "built-in" or account_data.get("name") != "admin":
        raise RuntimeError("Unable to authenticate the seeded Casdoor admin account for bootstrap user creation.")


def _bootstrap_casdoor_login_user(answers: InstallerAnswers) -> dict[str, Any] | None:
    if not _casdoor_bootstrap_identity_enabled(answers):
        return None

    base_url, host_headers = _casdoor_bootstrap_endpoint(answers)
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib_request.build_opener(urllib_request.HTTPCookieProcessor(cookie_jar))
    login_username = str(answers.bootstrap_login_username or "").strip()
    payload = {
        "owner": "built-in",
        "name": login_username,
        "displayName": str(answers.bootstrap_login_display_name or "").strip(),
        "email": str(answers.bootstrap_login_email or "").strip(),
        "password": str(answers.bootstrap_login_password or ""),
        "passwordType": "plain",
        "signupApplication": "app-built-in",
        "type": "normal-user",
        "isAdmin": True,
        "isForbidden": False,
        "isDeleted": False,
    }

    last_error: Exception | None = None
    for _ in range(CASDOOR_BOOTSTRAP_MAX_ATTEMPTS):
        try:
            _casdoor_login_admin(opener, base_url, host_headers)
            user_id = urllib_parse.quote(f"built-in/{login_username}", safe="")
            existing = _urlopen_json(
                opener,
                f"{base_url.rstrip('/')}/api/get-user?id={user_id}",
                headers={**host_headers, "Accept": "application/json"},
            )
            exists = existing.get("status") == "ok" and isinstance(existing.get("data"), dict) and existing["data"].get("name") == login_username
            endpoint = "/api/update-user" if exists else "/api/add-user"
            request_url = f"{base_url.rstrip('/')}{endpoint}"
            if exists:
                request_url = f"{request_url}?id={user_id}"
            response = _urlopen_json(
                opener,
                request_url,
                method="POST",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    **host_headers,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            if response.get("status") != "ok":
                raise RuntimeError(str(response.get("msg") or "Casdoor bootstrap user operation failed"))
            return {
                "username": login_username,
                "email": payload["email"],
                "display_name": payload["displayName"],
                "password": payload["password"],
                "password_generated": bool(answers.bootstrap_login_password_generated),
            }
        except (urllib_error.URLError, TimeoutError, RuntimeError, OSError) as exc:
            last_error = exc
            time.sleep(CASDOOR_BOOTSTRAP_RETRY_DELAY_SECONDS)
    raise RuntimeError(
        "Unable to provision bootstrap Casdoor login user after waiting for the local gateway and Casdoor to become ready: "
        f"{last_error}"
    )


def _require_docker_stack_prerequisites(env: dict[str, str]) -> None:
    docker_check = run_command(["docker", "compose", "version"], check=False, env=env)
    if docker_check.returncode != 0:
        raise SystemExit("Docker Compose v2 is required on PATH before the installer can auto-start the stack.")
    daemon_check = run_command(["docker", "info"], check=False, env=env)
    if daemon_check.returncode != 0:
        raise SystemExit("Docker is installed but the daemon is not ready. Start Docker Desktop or the docker service and rerun the installer.")


def _auto_start_stack(install_root: Path, env: dict[str, str]) -> list[str]:
    run_command(compose_prefix(local=False, root=install_root) + ["up", "-d", "--remove-orphans"], cwd=install_root, env=env)
    return portal_urls(root=install_root)


def main() -> None:
    source_root = source_repo_root()
    mode = _install_mode(source_root)
    install_root = source_root if mode == "editable" else _prepare_install_root(source_root)
    os.environ[FRONTIER_APP_HOME_ENV] = str(install_root)
    answers = _collect_installer_answers(install_root)
    path_update = _ensure_scripts_path(mode)
    _write_secure_installer_env(install_root, answers)
    compose_env = ensure_compose_env_file(local_profile=False, root=install_root)
    _best_effort_owner_only_permissions(compose_env)
    install_env = _runtime_env(install_root, mode)
    run_command(_pip_install_args(install_root), cwd=install_root, env=install_env)
    _require_docker_stack_prerequisites(install_env)
    urls = _auto_start_stack(install_root, install_env)
    bootstrap_login = _bootstrap_casdoor_login_user(answers)
    next_steps = [
        "Open one of the URLs above to reach the portal.",
        "Run ``lattix health`` to verify backend readiness.",
        "Use the hosted or enterprise deployment path when you need per-agent workload isolation beyond the secure local single-host profile.",
    ]
    if bootstrap_login is not None:
        bootstrap_username = str(bootstrap_login.get("username") or "").strip()
        if bootstrap_username:
            next_steps.insert(1, f"Sign in via /auth using {bootstrap_username} once the stack is ready.")
    _print_install_result(
        {
            "installed": True,
            "install_mode": mode,
            "repo_root": str(install_root),
            "compose_env": str(compose_env.resolve()),
            "auto_started": True,
            "urls": urls,
            "path": path_update,
            "auth_mode": answers.local_auth_provider,
            "security_posture": "Secure local profile (single-host compose, authenticated A2A)",
            "bootstrap_url": bootstrap_url(),
            "bootstrap_login": bootstrap_login,
            "next_steps": next_steps,
        }
    )


if __name__ == "__main__":
    main()
