"""Application configuration models for the root Frontier platform."""

from __future__ import annotations

from functools import lru_cache
import json

from pydantic import Field, model_validator

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover - compatibility fallback for minimal environments.
    from pydantic import BaseModel as BaseSettings  # type: ignore[misc,assignment]

    def SettingsConfigDict(**kwargs: object) -> dict[str, object]:
        return dict(kwargs)


class Settings(BaseSettings):
    """Centralized environment-backed settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "lattix-frontier"
    app_env: str = Field(default="development", alias="FRONTIER_ENV")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: str = Field(default="sqlite:///frontier.db", alias="DATABASE_URL")
    state_store_path: str = Field(default=".frontier/state.db", alias="FRONTIER_STATE_STORE")
    vault_addr: str = Field(default="http://localhost:8200", alias="VAULT_ADDR")
    vault_token: str = Field(default="dev-root-token", alias="VAULT_TOKEN")
    opa_addr: str = Field(default="http://localhost:8181", alias="OPA_ADDR")
    nats_url: str = Field(default="nats://localhost:4222", alias="NATS_URL")
    nats_subject: str = Field(default="frontier.events", alias="NATS_SUBJECT")
    nats_stream: str = Field(default="FRONTIER_EVENTS", alias="NATS_STREAM")
    jaeger_endpoint: str = Field(default="http://localhost:4317", alias="JAEGER_ENDPOINT")
    a2a_jwt_alg: str = Field(default="HS256", alias="A2A_JWT_ALG")
    a2a_jwt_issuer: str = Field(default="lattix-frontier", alias="A2A_JWT_ISS")
    a2a_jwt_audience: str = Field(default="agents", alias="A2A_JWT_AUD")
    a2a_jwt_secret: str | None = Field(default=None, alias="A2A_JWT_SECRET")
    a2a_jwt_private_key: str | None = Field(default=None, alias="A2A_JWT_PRIVATE_KEY")
    a2a_jwt_public_key: str | None = Field(default=None, alias="A2A_JWT_PUBLIC_KEY")
    a2a_require_nonce: bool = Field(default=True, alias="A2A_REQUIRE_NONCE")
    a2a_replay_protection: bool = Field(default=True, alias="A2A_REPLAY_PROTECTION")
    a2a_clock_skew_seconds: int = Field(default=30, alias="A2A_CLOCK_SKEW_SECONDS")
    a2a_replay_ttl_seconds: int = Field(default=900, alias="A2A_REPLAY_TTL_SECONDS")
    a2a_token_ttl_seconds: int = Field(default=30, alias="A2A_TOKEN_TTL_SECONDS")
    a2a_trusted_subjects_raw: str = Field(default="", alias="A2A_TRUSTED_SUBJECTS")
    event_signing_keys_json: str = Field(default="", alias="EVENT_SIGNING_KEYS_JSON")
    allowed_egress_hosts_raw: str = Field(default="", alias="ALLOWED_EGRESS_HOSTS")
    sandbox_runner_image: str = Field(default="python:3.12-slim", alias="SANDBOX_RUNNER_IMAGE")
    sandbox_internal_network: str = Field(default="frontier-sandbox-internal", alias="SANDBOX_INTERNAL_NETWORK")
    sandbox_egress_gateway: str = Field(default="sandbox-egress-gateway:3128", alias="SANDBOX_EGRESS_GATEWAY")
    sandbox_workspace_root: str = Field(default=".sandbox", alias="SANDBOX_WORKSPACE_ROOT")
    sandbox_allow_live_execution: bool = Field(default=False, alias="SANDBOX_ALLOW_LIVE_EXECUTION")
    sandbox_default_timeout_seconds: int = Field(default=120, alias="SANDBOX_DEFAULT_TIMEOUT_SECONDS")
    sandbox_default_memory_mb: int = Field(default=512, alias="SANDBOX_DEFAULT_MEMORY_MB")
    sandbox_default_cpu_limit: float = Field(default=1.0, alias="SANDBOX_DEFAULT_CPU_LIMIT")
    sandbox_default_pids_limit: int = Field(default=128, alias="SANDBOX_DEFAULT_PIDS_LIMIT")
    local_stack_host: str = Field(default="frontier.localhost", alias="LOCAL_STACK_HOST")
    local_gateway_http_port: int = Field(default=80, alias="LOCAL_GATEWAY_HTTP_PORT")
    installer_public_repo: str = Field(default="https://github.com/LATTIX-IO/lattix-xfrontier.git", alias="INSTALLER_PUBLIC_REPO")
    installer_default_ref: str = Field(default="main", alias="INSTALLER_DEFAULT_REF")
    federation_cluster_name: str = Field(default="local-frontier", alias="FEDERATION_CLUSTER_NAME")
    federation_region: str = Field(default="local", alias="FEDERATION_REGION")
    federation_enabled: bool = Field(default=False, alias="FEDERATION_ENABLED")
    federation_peer_endpoints: str = Field(default="", alias="FEDERATION_PEER_ENDPOINTS")
    default_budget_tokens: int = 100_000
    default_budget_seconds: int = 300
    default_budget_cost_usd: float = 1.0

    @property
    def a2a_trusted_subjects(self) -> set[str]:
        return {item.strip() for item in self.a2a_trusted_subjects_raw.split(",") if item.strip()}

    @property
    def allowed_egress_hosts(self) -> list[str]:
        return [item.strip() for item in self.allowed_egress_hosts_raw.split(",") if item.strip()]

    @property
    def event_signing_keys(self) -> dict[str, str]:
        if not self.event_signing_keys_json.strip():
            return {}
        loaded = json.loads(self.event_signing_keys_json)
        if not isinstance(loaded, dict):
            msg = "EVENT_SIGNING_KEYS_JSON must be a JSON object"
            raise ValueError(msg)
        return {str(key): str(value) for key, value in loaded.items()}

    @model_validator(mode="after")
    def validate_security_configuration(self) -> "Settings":
        placeholder_values = {"replace-with-local-dev-secret", "development-jwt-secret", "change-me-too", "change-me"}
        if self.a2a_jwt_alg.startswith("HS"):
            if not self.a2a_jwt_secret or self.a2a_jwt_secret in placeholder_values:
                msg = "A2A_JWT_SECRET must be provided with a non-placeholder value for HS* algorithms"
                raise ValueError(msg)
        else:
            if not self.a2a_jwt_private_key or not self.a2a_jwt_public_key:
                msg = "A2A_JWT_PRIVATE_KEY and A2A_JWT_PUBLIC_KEY are required for asymmetric A2A JWT algorithms"
                raise ValueError(msg)
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
