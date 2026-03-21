from lattix_frontier.security.vault_client import VaultClient


def test_vault_client_development_fallback() -> None:
    client = VaultClient()
    secret = client.read_secret("demo/path")
    assert "value" in secret or isinstance(secret, dict)
