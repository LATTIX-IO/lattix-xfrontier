from pathlib import Path
import secrets
import subprocess

import pytest

from frontier_tooling import installer as packaged_installer
from frontier_runtime.install import DiagnosticResult, FrontierInstaller, InstallerAnswers, MissingPrerequisite, PrerequisiteDefinition


def test_installer_writes_env_file(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("LOG_LEVEL=INFO\n", encoding="utf-8")
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        local_hostname="demo",
        oidc_provider_template="casdoor",
        oidc_issuer="http://casdoor.demo.localhost",
        oidc_audience="frontier-ui",
        oidc_jwks_url="http://casdoor.demo.localhost/.well-known/jwks.json",
        oidc_client_id="frontier-web",
        oidc_authorization_url="http://casdoor.demo.localhost/login/oauth/authorize",
        oidc_token_url="http://casdoor.demo.localhost/api/login/oauth/access_token",
        bootstrap_login_username="demo-login",
        bootstrap_login_email="demo-login@demo.localhost",
        bootstrap_login_display_name="Demo Login",
        bootstrap_login_password="DemoPass123!",
        openai_api_key="",
        federation_enabled=True,
        federation_cluster_name="cluster-a",
        federation_region="us-east",
        federation_peers=["https://peer.example.com"],
    )
    env_path = installer._write_env_file(
        answers,
        {
            "A2A_JWT_SECRET": secrets.token_urlsafe(32),
            "POSTGRES_PASSWORD": "db-secret",
            "NEO4J_PASSWORD": "neo-secret",
        },
    )
    text = env_path.read_text(encoding="utf-8")
    assert env_path == tmp_path / ".installer" / "local-secure.env"
    assert "LOCAL_STACK_HOST=demo.localhost" in text
    assert "FRONTIER_RUNTIME_PROFILE=local-secure" in text
    assert "NEXT_PUBLIC_API_BASE_URL=/api" in text
    assert "FRONTEND_ORIGIN=http://demo.localhost" in text
    assert "FRONTIER_REQUIRE_AUTHENTICATED_REQUESTS=true" in text
    assert "FRONTIER_ALLOW_HEADER_ACTOR_AUTH=false" in text
    assert "FRONTIER_LOCAL_BOOTSTRAP_AUTHENTICATED_OPERATOR=true" in text
    assert "FRONTIER_AUTH_MODE=oidc" in text
    assert "CASDOOR_LOCAL_HOST=casdoor.localhost" in text
    assert "CASDOOR_PUBLIC_URL=http://casdoor.localhost" in text
    assert "FRONTIER_BOOTSTRAP_ADMIN_USERNAME=frontier-admin" in text
    assert "FRONTIER_BOOTSTRAP_ADMIN_EMAIL=admin@demo.localhost" in text
    assert "FRONTIER_BOOTSTRAP_ADMIN_SUBJECT=frontier-admin" in text
    assert "FRONTIER_ADMIN_ACTORS=frontier-admin,admin@demo.localhost" in text
    assert "FRONTIER_BUILDER_ACTORS=frontier-admin,admin@demo.localhost" in text
    assert "CASDOOR_BOOTSTRAP_LOGIN_USERNAME=demo-login" in text
    assert "CASDOOR_BOOTSTRAP_LOGIN_EMAIL=demo-login@demo.localhost" in text
    assert "CASDOOR_BOOTSTRAP_LOGIN_DISPLAY_NAME=Demo Login" in text
    assert "CASDOOR_BOOTSTRAP_LOGIN_PASSWORD=DemoPass123!" in text
    assert "FRONTIER_API_BEARER_TOKEN=" in text
    assert "FRONTIER_AUTH_OIDC_PROVIDER=casdoor" in text
    assert "FRONTIER_AUTH_OIDC_ISSUER=http://casdoor.demo.localhost" in text
    assert "FRONTIER_AUTH_OIDC_AUDIENCE=frontier-ui" in text
    assert "FRONTIER_AUTH_OIDC_JWKS_URL=http://casdoor.demo.localhost/.well-known/jwks.json" in text
    assert "FRONTIER_AUTH_OIDC_CLIENT_ID=frontier-web" in text
    assert "FRONTIER_AUTH_OIDC_AUTHORIZATION_URL=http://casdoor.demo.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_TOKEN_URL=http://casdoor.demo.localhost/api/login/oauth/access_token" in text
    assert "FRONTIER_AUTH_OIDC_SIGNIN_URL=http://casdoor.demo.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_SIGNUP_URL=http://casdoor.demo.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_SCOPES=openid profile email" in text
    assert "A2A_JWT_AUD=frontier-runtime" in text
    assert "FEDERATION_ENABLED=true" in text
    assert "A2A_JWT_SECRET=" in text
    assert "POSTGRES_PASSWORD=db-secret" in text
    assert "NEO4J_PASSWORD=neo-secret" in text


def test_installer_generates_local_secret_when_blank(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(installation_root=str(tmp_path), deployment_mode="local")
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    secrets_map = installer._collect_local_secrets(answers)

    assert secrets_map["A2A_JWT_SECRET"]
    assert len(secrets_map["A2A_JWT_SECRET"]) >= 32
    assert secrets_map["POSTGRES_PASSWORD"]
    assert secrets_map["NEO4J_PASSWORD"]
    assert "FRONTIER_API_BEARER_TOKEN" not in secrets_map


def test_installer_reuses_existing_local_secrets_when_blank(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    installer_dir = tmp_path / ".installer"
    installer_dir.mkdir(parents=True, exist_ok=True)
    (installer_dir / "local-secure.env").write_text(
        "\n".join(
            [
                "A2A_JWT_SECRET=existing-a2a",
                "POSTGRES_PASSWORD=existing-postgres",
                "NEO4J_PASSWORD=existing-neo4j",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    answers = InstallerAnswers(installation_root=str(tmp_path), deployment_mode="local")
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    secrets_map = installer._collect_local_secrets(answers)

    assert secrets_map["A2A_JWT_SECRET"] == "existing-a2a"
    assert secrets_map["POSTGRES_PASSWORD"] == "existing-postgres"
    assert secrets_map["NEO4J_PASSWORD"] == "existing-neo4j"


def test_installer_reuses_existing_shared_token_when_blank(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    installer_dir = tmp_path / ".installer"
    installer_dir.mkdir(parents=True, exist_ok=True)
    (installer_dir / "local-secure.env").write_text(
        "\n".join(
            [
                "A2A_JWT_SECRET=existing-a2a",
                "POSTGRES_PASSWORD=existing-postgres",
                "NEO4J_PASSWORD=existing-neo4j",
                "FRONTIER_API_BEARER_TOKEN=existing-bearer",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        deployment_mode="local",
        local_auth_provider="shared-token",
    )
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    secrets_map = installer._collect_local_secrets(answers)

    assert secrets_map["FRONTIER_API_BEARER_TOKEN"] == "existing-bearer"


def test_secure_local_answers_generate_randomized_bootstrap_identity(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    monkeypatch.setattr("secrets.token_hex", lambda _: "abc123")

    answers = installer.secure_local_answers(tmp_path)

    assert answers.local_hostname == "xfrontier"
    assert answers.local_auth_provider == "oidc"
    assert answers.oidc_provider_template == "casdoor"
    assert answers.bootstrap_admin_username == "frontier-admin-abc123"
    assert answers.bootstrap_admin_email == "frontier-admin-abc123@xfrontier.localhost"
    assert answers.bootstrap_admin_subject == "frontier-admin-abc123"
    assert answers.bootstrap_login_username == ""
    assert answers.bootstrap_login_email == ""
    assert answers.bootstrap_login_display_name == ""
    assert answers.bootstrap_login_password == ""
    assert answers.bootstrap_login_password_generated is False


def test_collect_local_answers_interactively_prompts_for_external_oidc(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    prompts = iter(
        [
            "demo",
            "oidc",
            "external",
            "https://login.example.com/realms/frontier",
            "frontier-api",
            "https://login.example.com/realms/frontier/protocol/openid-connect/certs",
            "frontier-ui",
            "https://login.example.com/realms/frontier/protocol/openid-connect/auth",
            "https://login.example.com/realms/frontier/protocol/openid-connect/token",
            "",
            "https://login.example.com/realms/frontier/registrations/start",
            "openid profile email groups",
            "",
            "",
            "",
            "y",
        ]
    )
    monkeypatch.setattr("secrets.token_hex", lambda _: "abc123")
    monkeypatch.setattr("builtins.input", lambda prompt: next(prompts))

    answers = installer.collect_local_answers(installation_root=tmp_path, interactive=True)

    assert answers.local_hostname == "demo"
    assert answers.local_auth_provider == "oidc"
    assert answers.oidc_provider_template == "external"
    assert answers.oidc_issuer == "https://login.example.com/realms/frontier"
    assert answers.oidc_audience == "frontier-api"
    assert answers.oidc_jwks_url.endswith("/certs")
    assert answers.oidc_client_id == "frontier-ui"
    assert answers.oidc_authorization_url.endswith("/auth")
    assert answers.oidc_token_url.endswith("/token")
    assert answers.oidc_signin_url == answers.oidc_authorization_url
    assert answers.oidc_signup_url.endswith("/registrations/start")
    assert answers.oidc_scopes == ["openid", "profile", "email", "groups"]
    assert answers.bootstrap_admin_username == "frontier-admin-abc123"
    assert answers.bootstrap_admin_email == "frontier-admin-abc123@demo.localhost"
    assert answers.bootstrap_admin_subject == "frontier-admin-abc123"


def test_render_panel_produces_boxed_tui_output(tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)

    panel = installer._render_panel("Sample", ["Line one", "Line two"])
    lines = panel.splitlines()

    assert "╔" in panel
    assert "Sample" in panel
    assert "Line one" in panel
    assert "╚" in panel
    assert len({len(line) for line in lines}) == 1


def test_collect_local_answers_prints_review_tui(monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    prompts = iter(["", "", "", "", "", "", "review-user", "review@example.com", "Review User", "y"])
    monkeypatch.setattr("secrets.token_hex", lambda _: "abc123")
    monkeypatch.setattr("getpass.getpass", lambda prompt: "ReviewPass123!")
    monkeypatch.setattr("builtins.input", lambda prompt: next(prompts))

    answers = installer.collect_local_answers(installation_root=tmp_path, interactive=True)

    captured = capsys.readouterr()
    assert answers.bootstrap_admin_username == "frontier-admin-abc123"
    assert answers.bootstrap_login_username == "review-user"
    assert answers.bootstrap_login_password == "ReviewPass123!"
    assert "Lattix xFrontier installer" in captured.out
    assert "Review install settings" in captured.out
    assert "Secure local installation wizard" in captured.out
    assert "Login user  : review-user" in captured.out


def test_collect_local_answers_requires_interactive_casdoor_login_input(tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)

    with pytest.raises(SystemExit, match="Interactive installer input is required to create the Casdoor bootstrap login user"):
        installer.collect_local_answers(installation_root=tmp_path, interactive=False)


def test_collect_local_answers_prompts_for_casdoor_login_bootstrap(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    prompts = iter([
        "demo",
        "oidc",
        "casdoor",
        "frontier-admin-demo",
        "admin@demo.localhost",
        "frontier-admin-demo",
        "frontier-login-demo",
        "login@demo.localhost",
        "Demo Operator",
        "y",
    ])
    monkeypatch.setattr("secrets.token_hex", lambda _: "abc123")
    monkeypatch.setattr("builtins.input", lambda prompt: next(prompts))
    monkeypatch.setattr("getpass.getpass", lambda prompt: "LoginPass123!")

    answers = installer.collect_local_answers(installation_root=tmp_path, interactive=True)

    assert answers.bootstrap_login_username == "frontier-login-demo"
    assert answers.bootstrap_login_email == "login@demo.localhost"
    assert answers.bootstrap_login_display_name == "Demo Operator"
    assert answers.bootstrap_login_password == "LoginPass123!"
    assert answers.bootstrap_login_password_generated is False


def test_collect_local_answers_reprompts_for_required_casdoor_login_fields(monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    prompts = iter([
        "demo",
        "oidc",
        "casdoor",
        "frontier-admin-demo",
        "admin@demo.localhost",
        "frontier-admin-demo",
        "",
        "required-user",
        "",
        "required@example.com",
        "",
        "Required User",
        "y",
    ])
    secrets_iter = iter(["", "RequiredPass123!"])
    monkeypatch.setattr("secrets.token_hex", lambda _: "abc123")
    monkeypatch.setattr("builtins.input", lambda prompt: next(prompts))
    monkeypatch.setattr("getpass.getpass", lambda prompt: next(secrets_iter))

    answers = installer.collect_local_answers(installation_root=tmp_path, interactive=True)

    captured = capsys.readouterr()
    assert answers.bootstrap_login_username == "required-user"
    assert answers.bootstrap_login_email == "required@example.com"
    assert answers.bootstrap_login_display_name == "Required User"
    assert answers.bootstrap_login_password == "RequiredPass123!"
    assert captured.out.count("A value is required.") >= 4


def test_packaged_installer_bootstraps_casdoor_login_user(monkeypatch, tmp_path: Path) -> None:
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        local_auth_provider="oidc",
        oidc_provider_template="casdoor",
        oidc_issuer="http://casdoor.localhost",
        bootstrap_login_username="demo-login",
        bootstrap_login_email="demo-login@demo.localhost",
        bootstrap_login_display_name="Demo Login",
        bootstrap_login_password="DemoPass123!",
        bootstrap_login_password_generated=True,
    )

    captured_requests: list[tuple[str, str, str | None, dict[str, str]]] = []

    class DummyOpener:
        def open(self, request, timeout=10):
            captured_requests.append(
                (
                    request.full_url,
                    request.get_method(),
                    request.data.decode("utf-8") if request.data else None,
                    dict(request.header_items()),
                )
            )

            class DummyResponse:
                def __init__(self, payload: str) -> None:
                    self._payload = payload

                def read(self) -> bytes:
                    return self._payload.encode("utf-8")

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            if request.full_url.endswith("/api/get-account"):
                return DummyResponse('{"status":"ok","data":{"owner":"built-in","name":"admin"}}')
            if "/api/get-user" in request.full_url:
                return DummyResponse('{"status":"error","msg":"not found"}')
            if request.full_url.endswith("/api/add-user"):
                return DummyResponse('{"status":"ok","data":"Affected"}')
            return DummyResponse('{"status":"error","msg":"ignored"}')

    monkeypatch.setattr(packaged_installer.urllib_request, "build_opener", lambda *args: DummyOpener())

    bootstrap_login = packaged_installer._bootstrap_casdoor_login_user(answers)

    assert bootstrap_login == {
        "username": "demo-login",
        "email": "demo-login@demo.localhost",
        "display_name": "Demo Login",
        "password": "DemoPass123!",
        "password_generated": True,
    }
    assert any(url.endswith("/api/get-account") for url, *_ in captured_requests)
    add_user_request = next(item for item in captured_requests if item[0].endswith("/api/add-user"))
    assert add_user_request[1] == "POST"
    assert '"name": "demo-login"' in add_user_request[2]
    assert add_user_request[3]["Host"] == "casdoor.localhost"


def test_packaged_installer_retries_transient_casdoor_gateway_failures(monkeypatch, tmp_path: Path) -> None:
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        local_auth_provider="oidc",
        oidc_provider_template="casdoor",
        oidc_issuer="http://casdoor.localhost",
        bootstrap_login_username="demo-login",
        bootstrap_login_email="demo-login@demo.localhost",
        bootstrap_login_display_name="Demo Login",
        bootstrap_login_password="DemoPass123!",
        bootstrap_login_password_generated=True,
    )

    attempts = {"count": 0}

    class DummyOpener:
        def open(self, request, timeout=10):
            attempts["count"] += 1

            class DummyResponse:
                def __init__(self, payload: str) -> None:
                    self._payload = payload

                def read(self) -> bytes:
                    return self._payload.encode("utf-8")

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb) -> bool:
                    return False

            if attempts["count"] <= 2:
                raise packaged_installer.urllib_error.HTTPError(request.full_url, 502, "Bad Gateway", hdrs=None, fp=None)
            if request.full_url.endswith("/api/get-account"):
                return DummyResponse('{"status":"ok","data":{"owner":"built-in","name":"admin"}}')
            if "/api/get-user" in request.full_url:
                return DummyResponse('{"status":"error","msg":"not found"}')
            if request.full_url.endswith("/api/add-user"):
                return DummyResponse('{"status":"ok","data":"Affected"}')
            return DummyResponse('{"status":"error","msg":"ignored"}')

    monkeypatch.setattr(packaged_installer.urllib_request, "build_opener", lambda *args: DummyOpener())
    monkeypatch.setattr(packaged_installer.time, "sleep", lambda *_: None)

    bootstrap_login = packaged_installer._bootstrap_casdoor_login_user(answers)

    assert attempts["count"] >= 3
    assert bootstrap_login is not None
    assert bootstrap_login["username"] == "demo-login"


def test_packaged_installer_targets_active_scripts_dir_for_editable_install(monkeypatch, tmp_path: Path) -> None:
    editable_scripts = tmp_path / ".venv" / "Scripts"
    user_scripts = tmp_path / "AppData" / "Roaming" / "Python" / "Scripts"
    monkeypatch.setattr(packaged_installer, "python_scripts_dir", lambda: editable_scripts)
    monkeypatch.setattr(packaged_installer, "user_scripts_dir", lambda: user_scripts)

    assert packaged_installer._scripts_dir_for_install_mode("editable") == editable_scripts
    assert packaged_installer._scripts_dir_for_install_mode("wheel") == user_scripts


def test_packaged_installer_runtime_env_prepends_editable_scripts_dir(monkeypatch, tmp_path: Path) -> None:
    editable_scripts = tmp_path / ".venv" / "Scripts"
    monkeypatch.setattr(packaged_installer, "_scripts_dir_for_install_mode", lambda mode: editable_scripts)
    monkeypatch.setenv("PATH", str(tmp_path / "Windows" / "System32"))

    env = packaged_installer._runtime_env(tmp_path, "editable")

    assert env["PATH"].split(";", 1)[0] == str(editable_scripts)
    assert env[packaged_installer.FRONTIER_APP_HOME_ENV] == str(tmp_path)


def test_packaged_installer_update_preserves_installer_state(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    install_root = tmp_path / "installed"
    (source_root / "frontier_tooling").mkdir(parents=True, exist_ok=True)
    (source_root / "pyproject.toml").write_text("[project]\nname='lattix-frontier'\nversion='0.2.0'\n", encoding="utf-8")
    (source_root / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (source_root / "README.md").write_text("new build\n", encoding="utf-8")

    (install_root / ".installer").mkdir(parents=True, exist_ok=True)
    (install_root / ".installer" / "local-secure.env").write_text("A2A_JWT_SECRET=existing-secret\n", encoding="utf-8")
    (install_root / ".env").write_text("LOCAL_STACK_HOST=xfrontier.local\n", encoding="utf-8")
    (install_root / "README.md").write_text("old build\n", encoding="utf-8")

    refreshed_root = packaged_installer._prepare_install_root_for_update(source_root, install_root)

    assert refreshed_root == install_root
    assert (install_root / ".installer" / "local-secure.env").read_text(encoding="utf-8") == "A2A_JWT_SECRET=existing-secret\n"
    assert (install_root / ".env").read_text(encoding="utf-8") == "LOCAL_STACK_HOST=xfrontier.local\n"
    assert (install_root / "README.md").read_text(encoding="utf-8") == "new build\n"


def test_packaged_installer_retries_secure_gateway_on_fallback_port(monkeypatch, tmp_path: Path) -> None:
    installer_dir = tmp_path / ".installer"
    installer_dir.mkdir(parents=True, exist_ok=True)
    compose_env = installer_dir / "local-secure.env"
    compose_env.write_text(
        "\n".join(
            [
                "LOCAL_STACK_HOST=xfrontier.local",
                "LOCAL_GATEWAY_BIND_HOST=127.0.0.1",
                "LOCAL_GATEWAY_HTTP_PORT=80",
                "FRONTEND_ORIGIN=http://xfrontier.local",
                "FRONTIER_LOCAL_API_BASE_URL=http://127.0.0.1/api",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    calls: list[list[str]] = []

    def _fake_compose_run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        current_env_lines = compose_env.read_text(encoding="utf-8").splitlines()
        if "LOCAL_GATEWAY_HTTP_PORT=80" in current_env_lines:
            return subprocess.CompletedProcess(
                command,
                1,
                stdout="",
                stderr="Error response from daemon: failed to set up container networking: driver failed programming external connectivity on endpoint xfrontier-local-gateway-1: Bind for 127.0.0.1:80 failed: port is already allocated\n",
            )
        return subprocess.CompletedProcess(command, 0, stdout="started\n", stderr="")

    monkeypatch.setattr(packaged_installer, "_compose_up_with_output", _fake_compose_run)
    monkeypatch.setattr(packaged_installer, "_select_fallback_gateway_port", lambda bind_host, occupied_port: 8080)
    monkeypatch.setattr(packaged_installer, "portal_urls", lambda root=None: ["http://xfrontier.local:8080", "http://127.0.0.1:8080"])

    urls = packaged_installer._auto_start_stack(tmp_path, {})
    updated_env = compose_env.read_text(encoding="utf-8")

    assert len(calls) == 2
    assert urls == ["http://xfrontier.local:8080", "http://127.0.0.1:8080"]
    assert "LOCAL_GATEWAY_HTTP_PORT=8080" in updated_env
    assert "FRONTEND_ORIGIN=http://xfrontier.local:8080" in updated_env
    assert "FRONTIER_LOCAL_API_BASE_URL=http://127.0.0.1:8080/api" in updated_env


def test_casdoor_bootstrap_endpoint_uses_effective_secure_gateway_port(monkeypatch, tmp_path: Path) -> None:
    installer_dir = tmp_path / ".installer"
    installer_dir.mkdir(parents=True, exist_ok=True)
    (installer_dir / "local-secure.env").write_text(
        "\n".join(
            [
                "LOCAL_GATEWAY_BIND_HOST=127.0.0.1",
                "LOCAL_GATEWAY_HTTP_PORT=8080",
                "LOCAL_STACK_HOST=xfrontier.local",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(packaged_installer.FRONTIER_APP_HOME_ENV, str(tmp_path))

    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        local_auth_provider="oidc",
        oidc_provider_template="casdoor",
        oidc_issuer="http://casdoor.localhost",
        bootstrap_login_username="demo-login",
        bootstrap_login_password="DemoPass123!",
    )

    base_url, host_headers = packaged_installer._casdoor_bootstrap_endpoint(answers)

    assert base_url == "http://127.0.0.1:8080"
    assert host_headers == {"Host": "casdoor.localhost"}


def test_installer_defaults_to_casdoor_oidc_preset(tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(installation_root=str(tmp_path), deployment_mode="local")

    env_path = installer._write_env_file(
        answers,
        {
            "A2A_JWT_SECRET": secrets.token_urlsafe(32),
            "POSTGRES_PASSWORD": "db-secret",
            "NEO4J_PASSWORD": "neo-secret",
        },
    )
    text = env_path.read_text(encoding="utf-8")

    assert "FRONTIER_AUTH_MODE=oidc" in text
    assert "FRONTIER_AUTH_OIDC_PROVIDER=casdoor" in text
    assert "FRONTIER_AUTH_OIDC_ISSUER=http://casdoor.localhost" in text
    assert "FRONTIER_AUTH_OIDC_AUDIENCE=frontier-ui" in text
    assert "FRONTIER_AUTH_OIDC_JWKS_URL=http://casdoor.localhost/.well-known/jwks.json" in text
    assert "FRONTIER_AUTH_OIDC_CLIENT_ID=frontier-web" in text
    assert "FRONTIER_AUTH_OIDC_AUTHORIZATION_URL=http://casdoor.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_TOKEN_URL=http://casdoor.localhost/api/login/oauth/access_token" in text


def test_installer_writes_casdoor_preset_when_selected(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        deployment_mode="local",
        local_auth_provider="oidc",
        oidc_provider_template="casdoor",
        oidc_issuer="http://casdoor.localhost",
        oidc_audience="frontier-ui",
        oidc_jwks_url="http://casdoor.localhost/.well-known/jwks.json",
        oidc_client_id="frontier-web",
        oidc_authorization_url="http://casdoor.localhost/login/oauth/authorize",
        oidc_token_url="http://casdoor.localhost/api/login/oauth/access_token",
    )
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    secrets_map = installer._collect_local_secrets(answers)
    env_path = installer._write_env_file(answers, secrets_map)
    text = env_path.read_text(encoding="utf-8")

    assert "FRONTIER_API_BEARER_TOKEN=" in text
    assert "FRONTIER_AUTH_MODE=oidc" in text
    assert "FRONTIER_AUTH_OIDC_PROVIDER=casdoor" in text
    assert "FRONTIER_AUTH_OIDC_ISSUER=http://casdoor.localhost" in text
    assert "FRONTIER_AUTH_OIDC_AUDIENCE=frontier-ui" in text
    assert "FRONTIER_AUTH_OIDC_JWKS_URL=http://casdoor.localhost/.well-known/jwks.json" in text
    assert "FRONTIER_AUTH_OIDC_CLIENT_ID=frontier-web" in text
    assert "FRONTIER_AUTH_OIDC_AUTHORIZATION_URL=http://casdoor.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_TOKEN_URL=http://casdoor.localhost/api/login/oauth/access_token" in text
    assert "FRONTIER_AUTH_OIDC_SIGNIN_URL=http://casdoor.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_SIGNUP_URL=http://casdoor.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_SCOPES=openid profile email" in text
    assert "FRONTIER_API_BEARER_TOKEN" not in secrets_map


def test_installer_treats_legacy_casdoor_mode_as_oidc(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        deployment_mode="local",
        local_auth_provider="casdoor",
    )
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    secrets_map = installer._collect_local_secrets(answers)
    env_path = installer._write_env_file(answers, secrets_map)
    text = env_path.read_text(encoding="utf-8")

    assert "FRONTIER_AUTH_MODE=oidc" in text
    assert "FRONTIER_AUTH_OIDC_PROVIDER=casdoor" in text
    assert "FRONTIER_AUTH_OIDC_SIGNIN_URL=http://casdoor.localhost/login/oauth/authorize" in text
    assert "FRONTIER_AUTH_OIDC_SIGNUP_URL=http://casdoor.localhost/login/oauth/authorize" in text
    assert "FRONTIER_API_BEARER_TOKEN" not in secrets_map


def test_installer_supports_external_oidc_provider(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        deployment_mode="local",
        local_auth_provider="oidc",
        oidc_provider_template="external",
        oidc_issuer="https://login.example.com/realms/frontier",
        oidc_audience="frontier-api",
        oidc_jwks_url="https://login.example.com/realms/frontier/protocol/openid-connect/certs",
        oidc_client_id="frontier-ui",
        oidc_authorization_url="https://login.example.com/realms/frontier/protocol/openid-connect/auth",
        oidc_token_url="https://login.example.com/realms/frontier/protocol/openid-connect/token",
        oidc_signin_url="https://login.example.com/realms/frontier/protocol/openid-connect/auth?prompt=login",
        oidc_signup_url="https://login.example.com/realms/frontier/registrations/start",
        oidc_scopes=["openid", "profile", "email", "groups"],
    )
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    secrets_map = installer._collect_local_secrets(answers)
    env_path = installer._write_env_file(answers, secrets_map)
    text = env_path.read_text(encoding="utf-8")

    assert "FRONTIER_AUTH_MODE=oidc" in text
    assert "FRONTIER_AUTH_OIDC_PROVIDER=oidc" in text
    assert "FRONTIER_AUTH_OIDC_ISSUER=https://login.example.com/realms/frontier" in text
    assert "FRONTIER_AUTH_OIDC_AUDIENCE=frontier-api" in text
    assert "FRONTIER_AUTH_OIDC_CLIENT_ID=frontier-ui" in text
    assert "FRONTIER_AUTH_OIDC_SIGNIN_URL=https://login.example.com/realms/frontier/protocol/openid-connect/auth?prompt=login" in text
    assert "FRONTIER_AUTH_OIDC_SIGNUP_URL=https://login.example.com/realms/frontier/registrations/start" in text
    assert "FRONTIER_AUTH_OIDC_SCOPES=openid profile email groups" in text
    assert "FRONTIER_API_BEARER_TOKEN" not in secrets_map


def test_installer_rejects_oidc_urls_with_embedded_credentials(tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        deployment_mode="local",
        local_auth_provider="oidc",
        oidc_provider_template="external",
        oidc_issuer="https://user:pass@login.example.com/realms/frontier",
        oidc_audience="frontier-api",
        oidc_jwks_url="https://login.example.com/realms/frontier/protocol/openid-connect/certs",
        oidc_client_id="frontier-ui",
        oidc_authorization_url="https://login.example.com/realms/frontier/protocol/openid-connect/auth",
        oidc_token_url="https://login.example.com/realms/frontier/protocol/openid-connect/token",
    )

    with pytest.raises(ValueError, match="must not embed credentials"):
        installer._write_env_file(
            answers,
            {
                "A2A_JWT_SECRET": secrets.token_urlsafe(32),
                "POSTGRES_PASSWORD": "db-secret",
                "NEO4J_PASSWORD": "neo-secret",
            },
        )


def test_installer_shared_token_mode_still_generates_bearer_secret(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        deployment_mode="local",
        local_auth_provider="shared-token",
    )
    monkeypatch.setattr("getpass.getpass", lambda prompt: "")

    secrets_map = installer._collect_local_secrets(answers)
    env_path = installer._write_env_file(answers, secrets_map)
    text = env_path.read_text(encoding="utf-8")

    assert secrets_map["FRONTIER_API_BEARER_TOKEN"]
    assert "FRONTIER_AUTH_MODE=shared-token" in text
    assert "FRONTIER_API_BEARER_TOKEN=" in text
    assert "FRONTIER_AUTH_OIDC_PROVIDER=" in text


def test_installer_does_not_collect_local_secret_for_enterprise_only(tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(installation_root=str(tmp_path), deployment_mode="enterprise")

    secrets_map = installer._collect_local_secrets(answers)

    assert secrets_map == {}


def test_installer_writes_helm_values(tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = InstallerAnswers(
        installation_root=str(tmp_path),
        deployment_mode="enterprise",
        federation_enabled=True,
        federation_cluster_name="cluster-a",
        federation_region="us-west",
        federation_peers=["https://peer-a.example.com", "https://peer-b.example.com"],
    )
    values_path = installer._write_generated_helm_values(answers)
    text = values_path.read_text(encoding="utf-8")
    assert "clusterName: cluster-a" in text
    assert "https://peer-a.example.com" in text


def test_resolve_missing_prerequisites_attempts_install_and_continues(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    definition = PrerequisiteDefinition(
        key="helm",
        display_name="Helm",
        check_name="command:helm",
        install_commands=(("winget", "install", "Helm.Helm"),),
        manual_steps=("Install Helm manually.",),
    )
    missing = [
        MissingPrerequisite(
            definition=definition,
            result=DiagnosticResult(name="command:helm", ok=False, message="missing from PATH"),
        )
    ]

    monkeypatch.setattr(installer, "_ask_yes_no", lambda prompt, default: True)
    monkeypatch.setattr(
        installer,
        "_run_install_command",
        lambda command: subprocess.CompletedProcess(command, 0, stdout="installed", stderr=""),
    )
    monkeypatch.setattr(
        installer,
        "_run_prerequisite_check",
        lambda definition: DiagnosticResult(name=definition.check_name, ok=True, message="found"),
    )

    installer._resolve_missing_prerequisites(missing, intro="Need Helm")


def test_resolve_missing_prerequisites_decline_exits_with_actionable_message(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    definition = PrerequisiteDefinition(
        key="kubectl",
        display_name="kubectl",
        check_name="command:kubectl",
        install_commands=(("winget", "install", "Kubernetes.kubectl"),),
        manual_steps=("Install kubectl manually.",),
    )
    missing = [
        MissingPrerequisite(
            definition=definition,
            result=DiagnosticResult(name="command:kubectl", ok=False, message="missing from PATH"),
        )
    ]

    monkeypatch.setattr(installer, "_ask_yes_no", lambda prompt, default: False)

    with pytest.raises(SystemExit) as excinfo:
        installer._resolve_missing_prerequisites(missing, intro="Need kubectl")

    message = str(excinfo.value)
    assert "Outstanding prerequisites" in message
    assert "kubectl" in message
    assert "winget install Kubernetes.kubectl" in message


def test_attempt_missing_prerequisites_reports_failed_install(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    definition = PrerequisiteDefinition(
        key="docker",
        display_name="Docker",
        check_name="command:docker",
        install_commands=(("winget", "install", "Docker.DockerDesktop"),),
        manual_steps=("Install Docker manually.",),
    )
    missing = [
        MissingPrerequisite(
            definition=definition,
            result=DiagnosticResult(name="command:docker", ok=False, message="missing from PATH"),
        )
    ]

    monkeypatch.setattr(
        installer,
        "_run_install_command",
        lambda command: subprocess.CompletedProcess(command, 1, stdout="", stderr="installer failed"),
    )

    unresolved = installer._attempt_missing_prerequisite_installs(missing)

    assert len(unresolved) == 1
    assert unresolved[0].result.message == "installer failed"


def test_installer_yes_no_accepts_default_and_explicit_answers(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = iter(["", "n", "yes"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    assert installer._ask_yes_no("Proceed?", True) is True
    assert installer._ask_yes_no("Proceed?", True) is False
    assert installer._ask_yes_no("Proceed?", False) is True


def test_installer_yes_no_reprompts_on_invalid_input(monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    answers = iter(["maybe", "Y"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    assert installer._ask_yes_no("Proceed?", False) is True
    captured = capsys.readouterr()
    assert "Please answer yes or no." in captured.out


def test_run_prerequisite_check_validates_named_commands(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    definition = PrerequisiteDefinition(
        key="helm",
        display_name="Helm",
        check_name="command:helm",
    )
    monkeypatch.setattr("shutil.which", lambda command: "C:/Tools/helm.exe" if command == "helm" else None)

    result = installer._run_prerequisite_check(definition)

    assert result.ok is True
    assert result.name == "command:helm"


def test_run_prerequisite_check_reports_missing_commands(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    definition = PrerequisiteDefinition(
        key="kubectl",
        display_name="kubectl",
        check_name="command:kubectl",
    )
    monkeypatch.setattr("shutil.which", lambda command: None)

    result = installer._run_prerequisite_check(definition)

    assert result.ok is False
    assert "kubectl is missing from PATH" == result.message


def test_attempt_missing_prerequisites_rechecks_after_install(monkeypatch, tmp_path: Path) -> None:
    installer = FrontierInstaller(repo_root=tmp_path)
    definition = PrerequisiteDefinition(
        key="helm",
        display_name="Helm",
        check_name="command:helm",
        install_commands=(("winget", "install", "Helm.Helm"),),
    )
    missing = [
        MissingPrerequisite(
            definition=definition,
            result=DiagnosticResult(name="command:helm", ok=False, message="missing from PATH"),
        )
    ]
    monkeypatch.setattr(
        installer,
        "_run_install_command",
        lambda command: subprocess.CompletedProcess(command, 0, stdout="installed", stderr=""),
    )
    monkeypatch.setattr(
        installer,
        "_run_prerequisite_check",
        lambda definition: DiagnosticResult(name=definition.check_name, ok=False, message="still missing after install"),
    )

    unresolved = installer._attempt_missing_prerequisite_installs(missing)

    assert len(unresolved) == 1
    assert unresolved[0].result.message == "still missing after install"