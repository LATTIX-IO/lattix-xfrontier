"""Frozen backend-sidecar entrypoint for the Tauri desktop bundle.

This is the script PyInstaller/Nuitka packages and Tauri spawns as its
``externalBin`` sidecar. On launch it:
  1. makes the bundled binaries (Node, NATS, …) discoverable via PATH,
  2. runs first-run provisioning (fetch heavy sidecars + pull the model) — a
     no-op once everything is present,
  3. runs the native supervisor in the foreground (backend + frontend + sidecars
     + agents), then blocks until the shell terminates it.
"""

from __future__ import annotations

import os
import sys


def _prepend_bundled_bin_to_path() -> None:
    """Make bundled binaries (Node, NATS, the backend) discoverable by name."""
    from .desktop import bundled_bin_dir

    bundled = str(bundled_bin_dir())
    current = os.environ.get("PATH", "")
    if bundled and bundled not in current.split(os.pathsep):
        os.environ["PATH"] = bundled + os.pathsep + current if current else bundled


def main() -> None:
    from .desktop import run_desktop_supervisor, writable_bin_dir
    from .desktop_firstrun import ensure_sidecars

    _prepend_bundled_bin_to_path()
    try:
        ensure_sidecars(writable_bin_dir())
    except Exception as exc:  # noqa: BLE001 - never block boot on provisioning
        print(f"[firstrun] provisioning error (continuing degraded): {exc}", flush=True)
    run_desktop_supervisor()


if __name__ == "__main__":
    sys.exit(main())
