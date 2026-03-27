from __future__ import annotations

import os
from pathlib import Path
import platform
import json
import http.client
import re
import shutil
import ssl
import stat
import socket
import subprocess
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
_LOCAL_GATEWAY_PORT_FALLBACKS = (8080, 8081, 8088, 8888)


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


def _path_separator_for_scripts_dir(scripts_dir: Path, current_path: str) -> str:
    if ";" in current_path:
        return ";"
    if scripts_dir.name.lower() == "scripts":
        return ";"
    return os.pathsep


def _runtime_env(install_root: Path, mode: str) -> dict[str, str]:
    scripts_dir = _scripts_dir_for_install_mode(mode)
    current_path = str(os.getenv("PATH") or "")
    path_separator = _path_separator_for_scripts_dir(scripts_dir, current_path)
    path_entries = [entry for entry in current_path.split(path_separator) if entry]
    if str(scripts_dir) not in path_entries:
        path_entries.insert(0, str(scripts_dir))
    env = os.environ.copy()
    env["PATH"] = path_separator.join(path_entries)
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


def _preserve_existing_install_state(existing_root: Path, staged_root: Path) -> None:
    for relative_name in (".installer", ".env"):
        source_path = existing_root / relative_name
        if not source_path.exists():
            continue
        target_path = staged_root / relative_name
        if source_path.is_dir():
            shutil.copytree(source_path, target_path, dirs_exist_ok=True)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)


def _prepare_install_root_for_update(source_root: Path, existing_root: Path) -> Path:
    install_root = existing_root.resolve(strict=False)
    install_root.parent.mkdir(parents=True, exist_ok=True)
    staging_parent = Path(tempfile.mkdtemp(prefix="frontier-app-update-", dir=str(install_root.parent)))
    staged_root = staging_parent / install_root.name
    try:
        shutil.copytree(source_root, staged_root, ignore=_source_copy_ignore)
        if install_root.exists():
            _preserve_existing_install_state(install_root, staged_root)
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


def _refresh_existing_local_stacks(install_root: Path, env: dict[str, str]) -> tuple[list[str], list[str]]:
    refreshed_profiles: list[str] = []
    urls: list[str] = []
    secure_env_path = install_root / ".installer" / "local-secure.env"
    lightweight_env_path = install_root / ".installer" / "local-lightweight.env"

    if secure_env_path.exists() or not lightweight_env_path.exists():
        run_command(compose_prefix(local=False, root=install_root) + ["up", "-d", "--build", "--remove-orphans"], cwd=install_root, env=env)
        refreshed_profiles.append("secure")
        urls = portal_urls(root=install_root)

    if lightweight_env_path.exists():
        run_command(compose_prefix(local=True, root=install_root) + ["up", "-d", "--build", "--remove-orphans"], cwd=install_root, env=env)
        refreshed_profiles.append("lightweight")

    return refreshed_profiles, urls


def _git_stdout(args: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    completed = subprocess.run(
        args,
        cwd=str(cwd),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "git command failed").strip()
        raise SystemExit(message)
    return (completed.stdout or "").strip()


def _update_editable_checkout(install_root: Path, env: dict[str, str]) -> tuple[str, str]:
    status_output = _git_stdout(["git", "status", "--porcelain"], cwd=install_root, env=env)
    if status_output:
        raise SystemExit(
            "The editable xFrontier checkout has local changes. Commit or stash them before running `lattix update` so the updater does not overwrite work in progress."
        )

    branch = _git_stdout(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=install_root, env=env) or "main"
    before_ref = _git_stdout(["git", "rev-parse", "HEAD"], cwd=install_root, env=env)
    run_command(["git", "pull", "--ff-only"], cwd=install_root, env=env)
    after_ref = _git_stdout(["git", "rev-parse", "HEAD"], cwd=install_root, env=env)
    return branch, "updated" if before_ref != after_ref else "already-current"


def _validated_archive_download_url(url: str) -> str:
    parsed = urlsplit(str(url or "").strip())
    if parsed.scheme.lower() not in {"http", "https"}:
        raise SystemExit("Installer archive URL must use http or https.")
    if not parsed.hostname:
        raise SystemExit("Installer archive URL must include a host.")
    if parsed.username or parsed.password:
        raise SystemExit("Installer archive URL must not include credentials.")
    if parsed.fragment:
        raise SystemExit("Installer archive URL must not include fragments.")
    return parsed.geturl()


def _download_url_bytes(url: str, *, redirects_remaining: int = 3) -> bytes:
    validated_url = _validated_archive_download_url(url)
    parsed = urlsplit(validated_url)
    hostname = parsed.hostname
    if not hostname:
        raise SystemExit("Installer archive URL must include a host.")
    connection: http.client.HTTPConnection
    if parsed.scheme.lower() == "https":
        # nosemgrep: python.lang.security.audit.httpsconnection-detected.httpsconnection-detected
        connection = http.client.HTTPSConnection(
            hostname,
            parsed.port,
            timeout=30,
            context=ssl.create_default_context(),
        )
    else:
        connection = http.client.HTTPConnection(hostname, parsed.port, timeout=30)

    target = parsed.path or "/"
    if parsed.query:
        target = f"{target}?{parsed.query}"

    try:
        connection.request("GET", target, headers={"User-Agent": "frontier-updater/1.0"})
        response = connection.getresponse()
        if response.status in {301, 302, 303, 307, 308}:
            location = response.getheader("Location")
            if not location or redirects_remaining <= 0:
                raise SystemExit("Installer archive download redirected too many times.")
            return _download_url_bytes(urllib_parse.urljoin(validated_url, location), redirects_remaining=redirects_remaining - 1)
        if response.status >= 400:
            raise SystemExit(f"Installer archive download failed with HTTP {response.status}.")
        return response.read()
    finally:
        connection.close()


def _download_update_archive(target_dir: Path) -> Path:
    archive_url = bootstrap_url()
    archive_bytes = _download_url_bytes(archive_url)
    archive_path = target_dir / "update.zip"
    archive_path.write_bytes(archive_bytes)
    unpack_dir = target_dir / "archive"
    shutil.unpack_archive(str(archive_path), str(unpack_dir))
    extracted_roots = [path for path in unpack_dir.iterdir() if path.is_dir()]
    if not extracted_roots:
        raise SystemExit("Downloaded update archive did not contain a repository directory.")
    return extracted_roots[0]


def _update_published_install(install_root: Path) -> str:
    temp_root = Path(tempfile.mkdtemp(prefix="frontier-update-download-"))
    try:
        source_root = _download_update_archive(temp_root)
        _prepare_install_root_for_update(source_root, install_root)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    return "updated"


def _print_update_result(payload: dict[str, Any]) -> None:
    if _display_mode() == "json":
        print_json(payload)
        return

    lines = [
        f"Status      : {'Ready' if payload.get('updated') else 'No changes'}",
        f"Mode        : {_friendly_install_mode(str(payload.get('install_mode') or 'unknown'))}",
        f"App home    : {payload.get('repo_root')}",
        f"Env file    : {payload.get('compose_env')}",
        f"CLI path    : {payload.get('path', {}).get('cli_path')}",
        f"Refresh     : {payload.get('refresh_status')}",
    ]

    refreshed_profiles = payload.get("refreshed_profiles") if isinstance(payload.get("refreshed_profiles"), list) else []
    if refreshed_profiles:
        lines.append(f"Profiles    : {', '.join(str(item) for item in refreshed_profiles)}")

    urls = payload.get("urls") if isinstance(payload.get("urls"), list) else []
    if urls:
        lines.append("")
        lines.append("Portal URLs")
        for index, url in enumerate(urls, start=1):
            lines.append(f"  [{index}] {url}")

    next_steps = payload.get("next_steps") if isinstance(payload.get("next_steps"), list) else []
    if next_steps:
        lines.append("")
        lines.append("Next steps")
        for step in next_steps:
            lines.append(f"  • {step}")

    print(_render_box("Lattix xFrontier updated", lines))  # noqa: T201


def update() -> None:
    install_root = source_repo_root()
    mode = _install_mode(install_root)

    if mode == "wheel":
        refresh_status = _update_published_install(install_root)

    path_update = _ensure_scripts_path(mode)
    install_env = _runtime_env(install_root, mode)

    if mode == "editable":
        branch, refresh_status = _update_editable_checkout(install_root, install_env)
    else:
        branch = "published"

    os.environ[FRONTIER_APP_HOME_ENV] = str(install_root)
    secure_env_path = install_root / ".installer" / "local-secure.env"
    lightweight_env_path = install_root / ".installer" / "local-lightweight.env"
    if secure_env_path.exists() or not lightweight_env_path.exists():
        compose_env = ensure_compose_env_file(local_profile=False, root=install_root)
    else:
        compose_env = ensure_compose_env_file(local_profile=True, root=install_root)
    _best_effort_owner_only_permissions(compose_env)
    run_command(_pip_install_args(install_root), cwd=install_root, env=install_env)
    _require_docker_stack_prerequisites(install_env)
    refreshed_profiles, urls = _refresh_existing_local_stacks(install_root, install_env)
    _print_update_result(
        {
            "updated": refresh_status == "updated",
            "install_mode": mode,
            "repo_root": str(install_root),
            "compose_env": str(compose_env.resolve()),
            "path": path_update,
            "refresh_status": refresh_status,
            "refreshed_profiles": refreshed_profiles,
            "urls": urls,
            "next_steps": [
                "Local workflows, agents, settings, and installer env files were preserved in place.",
                "Open one of the URLs above to verify the refreshed build.",
                "Run `lattix health` if you want to confirm backend readiness after the update.",
            ],
            "branch": branch,
        }
    )


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


def _read_installer_env_map(path: Path) -> dict[str, str]:
    env_map: dict[str, str] = {}
    if not path.exists():
        return env_map
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_map[key] = value
    return env_map


def _write_installer_env_map(path: Path, env_map: dict[str, str]) -> None:
    payload = "\n".join(f"{key}={value}" for key, value in env_map.items()) + "\n"
    path.write_text(payload, encoding="utf-8")


def _secure_gateway_origin(env_map: dict[str, str]) -> str:
    host = str(env_map.get("LOCAL_STACK_HOST") or "xfrontier.local").strip() or "xfrontier.local"
    port = str(env_map.get("LOCAL_GATEWAY_HTTP_PORT") or "80").strip() or "80"
    authority = host if port == "80" else f"{host}:{port}"
    return f"http://{authority}"


def _secure_local_api_base(env_map: dict[str, str]) -> str:
    bind_host = str(env_map.get("LOCAL_GATEWAY_BIND_HOST") or "127.0.0.1").strip() or "127.0.0.1"
    if bind_host == "0.0.0.0":
        bind_host = "127.0.0.1"
    port = str(env_map.get("LOCAL_GATEWAY_HTTP_PORT") or "80").strip() or "80"
    authority = bind_host if port == "80" else f"{bind_host}:{port}"
    return f"http://{authority}/api"


def _compose_up_with_output(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=str(cwd), env=env, check=False, capture_output=True, text=True)


def _port_conflict_from_compose_output(output: str) -> tuple[str, int] | None:
    match = re.search(r"Bind for (?P<host>[^:]+):(?P<port>\d+) failed: port is already allocated", output)
    if not match:
        return None
    return match.group("host"), int(match.group("port"))


def _port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def _select_fallback_gateway_port(bind_host: str, occupied_port: int) -> int | None:
    for candidate in _LOCAL_GATEWAY_PORT_FALLBACKS:
        if candidate == occupied_port:
            continue
        if _port_is_available(bind_host, candidate):
            return candidate
    return None


def _rewrite_secure_gateway_port(install_root: Path, gateway_port: int) -> Path:
    compose_env = ensure_compose_env_file(local_profile=False, root=install_root)
    env_map = _read_installer_env_map(compose_env)
    env_map["LOCAL_GATEWAY_HTTP_PORT"] = str(gateway_port)
    env_map["FRONTEND_ORIGIN"] = _secure_gateway_origin(env_map)
    env_map["FRONTIER_LOCAL_API_BASE_URL"] = _secure_local_api_base(env_map)
    _write_installer_env_map(compose_env, env_map)
    return compose_env


def _raise_compose_failure(command: list[str], completed: subprocess.CompletedProcess[str]) -> None:
    if completed.stdout:
        print(completed.stdout, end="", file=sys.stdout)
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    raise subprocess.CalledProcessError(completed.returncode, command, output=completed.stdout, stderr=completed.stderr)


def _auto_start_stack(install_root: Path, env: dict[str, str]) -> list[str]:
    command = compose_prefix(local=False, root=install_root) + ["up", "-d", "--remove-orphans"]
    completed = _compose_up_with_output(command, cwd=install_root, env=env)
    if completed.returncode == 0:
        return portal_urls(root=install_root)

    combined_output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    port_conflict = _port_conflict_from_compose_output(combined_output)
    if port_conflict is not None:
        bind_host, occupied_port = port_conflict
        fallback_port = _select_fallback_gateway_port(bind_host, occupied_port)
        if fallback_port is not None:
            _rewrite_secure_gateway_port(install_root, fallback_port)
            completed = _compose_up_with_output(command, cwd=install_root, env=env)
            if completed.returncode == 0:
                return portal_urls(root=install_root)

    _raise_compose_failure(command, completed)
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
