"""Secrets configuration loader."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


def _looks_like_sops_payload(content: str) -> bool:
    lowered = content.lower()
    return '"sops"' in lowered or "\nsops:" in lowered


def load_encrypted_config(path: Path) -> str:
    """Load configuration content, decrypting SOPS-managed files when available."""

    if shutil.which("sops") is not None:
        completed = subprocess.run(
            ["sops", "--decrypt", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0 and completed.stdout:
            return completed.stdout
    content = path.read_text(encoding="utf-8")
    if _looks_like_sops_payload(content):
        raise RuntimeError("Encrypted configuration requires SOPS to decrypt")
    return content
