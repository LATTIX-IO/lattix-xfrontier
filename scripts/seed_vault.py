"""Seed Vault with development placeholders."""

from __future__ import annotations

from lattix_frontier.security.vault_client import VaultClient


def main() -> None:
    client = VaultClient()
    print({"available": client.is_available()})  # noqa: T201


if __name__ == "__main__":
    main()
