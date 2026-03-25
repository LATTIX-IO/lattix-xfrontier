from __future__ import annotations

import os

from .common import DEFAULT_ARCHIVE_URL, ensure_compose_env_file, print_json, python_executable, repo_root, run_command


def bootstrap_url() -> str:
    return str(os.getenv("FRONTIER_ARCHIVE_URL", DEFAULT_ARCHIVE_URL))


def _install_mode(root) -> str:
    return "editable" if (root / ".git").exists() else "wheel"


def _pip_install_args(root) -> list[str]:
    args = [python_executable(), "-m", "pip", "install"]
    if _install_mode(root) == "editable":
        args.append("-e")
    args.append(".[dev]")
    return args


def main() -> None:
    root = repo_root()
    compose_env = ensure_compose_env_file(local_profile=False)
    mode = _install_mode(root)
    run_command(_pip_install_args(root), cwd=root)
    print_json(
        {
            "installed": True,
            "install_mode": mode,
            "repo_root": str(root),
            "compose_env": str(compose_env.resolve()),
            "next_steps": [
                "lattix up",
                "lattix health",
            ],
            "bootstrap_url": bootstrap_url(),
        }
    )


if __name__ == "__main__":
    main()
