from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

from .orchestrator import Orchestrator, registry_path_default


def run_workflow_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    orch = Orchestrator(Path(registry_path_default()))
    stages = spec.get("stages", [])
    last_env_json = None
    for st in stages:
        name = st.get("name", "stage")
        topic = st["topic"]
        payload = st.get("payload", {})
        budget_ms = int(st.get("budget_ms", 10_000))
        expected_keys = st.get("expected_keys")
        env = orch.run_stage(
            name=name,
            topic=topic,
            payload=payload,
            budget_ms=budget_ms,
            expected_keys=expected_keys,
        )
        last_env_json = env.to_json()
    return {"last_env": last_env_json}


def run_workflow_file(path: Path) -> Dict[str, Any]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    return run_workflow_spec(spec)
