import json

import pytest

from frontier_runtime.security import VaultClient


def test_vault_client_fails_closed_without_configuration() -> None:
    client = VaultClient(addr="", token="")

    with pytest.raises(RuntimeError, match="Vault client is not configured"):
        client.read_secret("demo/path")


def test_vault_client_reads_kv_v2_secret(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeResponse:
        def __enter__(self) -> "_FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"data": {"data": {"value": "super-secret", "enabled": True}}}).encode("utf-8")

    def _fake_urlopen(request, timeout=0):
        captured["url"] = request.full_url
        captured["token"] = request.get_header("X-vault-token")
        captured["accept"] = request.get_header("Accept")
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr("frontier_runtime.security.urlrequest.urlopen", _fake_urlopen)

    client = VaultClient(addr="http://vault:8200", token="vault-token", timeout_seconds=7)
    secret = client.read_secret("secret/data/demo/path")

    assert secret == {"value": "super-secret", "enabled": True}
    assert captured["url"] == "http://vault:8200/v1/secret/data/demo/path"
    assert captured["token"] == "vault-token"
    assert captured["accept"] == "application/json"
    assert captured["timeout"] == 7
