"""Seed Vault with development placeholders."""

from __future__ import annotations

import os

import hvac


def main() -> None:
    url = os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")
    token = os.getenv("VAULT_TOKEN", "dev-root-token")
    client = hvac.Client(url=url, token=token)
    if not client.is_authenticated():
        raise SystemExit("Vault is not authenticated. Set VAULT_ADDR and VAULT_TOKEN.")
    client.secrets.kv.v2.create_or_update_secret(
        path="dev/frontier",
        secret={
            "status": "seeded",
            "placeholder": "replace-me",
        },
        mount_point="secret",
    )
    print({"available": True, "seeded": "secret/data/dev/frontier", "vault_addr": url})  # noqa: T201


if __name__ == "__main__":
    main()
