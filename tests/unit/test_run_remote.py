from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from apps.workers.runtime.layer2.contracts import Envelope


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_run_remote_module():
    module_path = REPO_ROOT / "apps" / "workers" / "runtime" / "run_remote.py"
    module_name = "test_run_remote_module"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_remote_uses_orchestrator_remote_dispatch_path(monkeypatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    module = _load_run_remote_module()
    captured: dict[str, object] = {}

    class _FakeOrchestrator:
        def __init__(self, registry_path: Path) -> None:
            captured["registry_path"] = registry_path

        def run_stage(self, **kwargs):
            captured.update(kwargs)
            env = Envelope(topic=str(kwargs["topic"]), sender="orchestrator", payload={"remote_responses": [{"accepted": True, "via": "remote"}]})
            return env

    monkeypatch.setattr(module, "Orchestrator", _FakeOrchestrator)
    monkeypatch.setattr(module, "registry_path_default", lambda: tmp_path / "registry.json")
    monkeypatch.setattr(module, "topic_endpoints_map_path", lambda: tmp_path / "topic-map.json")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_remote.py",
            "security.compliance",
            "--payload",
            '{"task":"review"}',
            "--map",
            str(tmp_path / "topic-map.json"),
        ],
    )

    module.main()

    assert captured["name"] == "security.compliance-remote"
    assert captured["topic"] == "security.compliance"
    assert captured["payload"] == {"task": "review"}
    assert captured["dispatch_mode"] == "remote"
    assert captured["remote_map_path"] == (tmp_path / "topic-map.json").resolve()

    output = json.loads(capsys.readouterr().out)
    assert output["response"] == {"accepted": True, "via": "remote"}
