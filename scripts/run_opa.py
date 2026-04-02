"""Locate and execute the OPA CLI from PATH or the repo-local tools directory."""

from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import sys


def find_opa_binary() -> str:
    """Return the best available OPA executable path."""

    repo_root = Path(__file__).resolve().parents[1]
    local_candidates = [
        repo_root / ".tools" / "opa" / "opa.exe",
        repo_root / ".tools" / "opa" / "opa",
    ]
    for candidate in local_candidates:
        if candidate.exists():
            return str(candidate)
    path_candidate = shutil.which("opa")
    if path_candidate:
        return path_candidate
    raise RuntimeError(
        "OPA executable not found. Install it to .tools/opa/opa(.exe) or add 'opa' to PATH."
    )


def main(argv: list[str] | None = None) -> int:
    """Execute OPA with the provided command-line arguments."""

    args = list(sys.argv[1:] if argv is None else argv)
    command = [find_opa_binary(), *args]
    completed = subprocess.run(command, check=False, env=os.environ.copy())
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
