from __future__ import annotations
from typing import Dict, Any
from pathlib import Path
from ..orchestrator import Orchestrator, registry_path_default


def run(input_payload: Dict[str, Any]) -> None:
    orch = Orchestrator(Path(registry_path_default()))
    orch.run_stage("security-compliance", topic="security.compliance", payload=input_payload, budget_ms=8000)

