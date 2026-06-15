"""Track B4: desktop (Tauri) packaging integration — frozen-mode resolution,
desktop config, supervisor serve() lifecycle, and Tauri config validity.
Pure/unit; no Rust/PyInstaller build required."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from frontier_tooling import desktop as dt  # noqa: E402
from frontier_tooling import native_launcher as nl  # noqa: E402

_TAURI_DIR = _REPO_ROOT / "apps" / "desktop-tauri" / "src-tauri"


# --- frozen-mode resolution --------------------------------------------------
def test_is_frozen_default_false():
    assert dt.is_frozen() is False


def test_bundled_root_uses_meipass_when_set(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert dt.bundled_root() == tmp_path
    assert dt.bundled_bin_dir() == tmp_path / "bin"


def test_bundled_root_from_checkout_is_repo_root(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    # source_repo_root() is the package parent (repo root).
    assert (dt.bundled_root() / "frontier_tooling").exists()


def test_desktop_app_home_honors_env(monkeypatch, tmp_path):
    monkeypatch.setenv("FRONTIER_APP_HOME", str(tmp_path))
    assert dt.desktop_app_home() == tmp_path


# --- desktop NativeConfig ----------------------------------------------------
def test_desktop_config_uses_writable_bin_and_degrades(monkeypatch, tmp_path):
    monkeypatch.setenv("FRONTIER_APP_HOME", str(tmp_path))
    cfg = dt.desktop_config()
    assert cfg.app_home == tmp_path
    # First-run fetch lands in the writable app-home bin (not the read-only bundle).
    assert cfg.bin_dir == tmp_path / "bin"
    # Desktop degrades (boots before sidecars are fetched) rather than raising.
    assert cfg.degrade_when_missing is True


def test_desktop_config_overrides_pass_through(monkeypatch, tmp_path):
    monkeypatch.setenv("FRONTIER_APP_HOME", str(tmp_path))
    cfg = dt.desktop_config(enable_world_models=False)
    assert cfg.enable_world_models is False


# --- supervisor serve() lifecycle -------------------------------------------
def test_serve_starts_then_stops_on_interrupt():
    terminated: list[str] = []

    class _Proc:
        def __init__(self, name):
            self.name = name

        def poll(self):
            return None  # stays running

        def terminate(self):
            terminated.append(self.name)

    plan = nl.NativePlan(
        services=[
            nl.ServiceSpec(name="svc", argv=["svc"], health=nl.HealthCheck("none"), required=True)
        ],
        env={},
        warnings=[],
    )

    def _sleep(_s):
        raise KeyboardInterrupt  # first poll tick → simulate shell shutdown

    sup = nl.NativeSupervisor(
        plan,
        spawn=lambda argv, *, env, cwd: _Proc(argv[0]),
        run=lambda argv, *, env: 0,
        probe=lambda check: True,
        sleep=_sleep,
    )
    sup.serve()  # should not raise; start_all then stop_all
    assert terminated == ["svc"]


def test_serve_stops_when_required_service_dies():
    terminated: list[str] = []

    class _DeadProc:
        def poll(self):
            return 1  # already exited

        def terminate(self):
            terminated.append("svc")

    plan = nl.NativePlan(
        services=[
            nl.ServiceSpec(name="svc", argv=["svc"], health=nl.HealthCheck("none"), required=True)
        ],
        env={},
        warnings=[],
    )
    sup = nl.NativeSupervisor(
        plan,
        spawn=lambda argv, *, env, cwd: _DeadProc(),
        run=lambda argv, *, env: 0,
        probe=lambda check: True,
        sleep=lambda s: None,  # poll loop detects the dead required service
    )
    sup.serve()
    assert terminated == ["svc"]


# --- Tauri config validity ---------------------------------------------------
def test_tauri_conf_is_valid_and_complete():
    conf = json.loads((_TAURI_DIR / "tauri.conf.json").read_text(encoding="utf-8"))
    assert conf["identifier"] == "com.lattix.xfrontier"
    assert conf["bundle"]["externalBin"] == ["bin/frontier-backend"]
    # Auto-update is deferred (no signing key needed for test builds); the
    # updater plugin is intentionally absent until release.
    assert "updater" not in conf.get("plugins", {})
    # macOS hardened runtime + Windows timestamp server are configured for signing.
    assert conf["bundle"]["macOS"]["hardenedRuntime"] is True
    assert conf["bundle"]["windows"]["timestampUrl"]


def test_tauri_capabilities_allow_sidecar_spawn():
    cap = json.loads((_TAURI_DIR / "capabilities" / "default.json").read_text(encoding="utf-8"))
    spawn_perms = [
        p for p in cap["permissions"]
        if isinstance(p, dict) and p.get("identifier") == "shell:allow-spawn"
    ]
    assert spawn_perms, "sidecar spawn permission must be granted"
    assert spawn_perms[0]["allow"][0]["sidecar"] is True


def test_pyinstaller_spec_targets_desktop_main():
    spec = (_REPO_ROOT / "packaging" / "frontier-backend.spec").read_text(encoding="utf-8")
    assert "desktop_main.py" in spec
    assert "frontier-backend" in spec
