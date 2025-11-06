#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

from runtime.layer1.orchestrator import Orchestrator, registry_path_default
from runtime.layer3.agent_loader import register_agents


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a workflow with Layer 3 agent handlers")
    ap.add_argument("topic", help="Topic to emit (e.g., gtm.content)")
    ap.add_argument("--agents", help="Comma-separated agent IDs to include (optional)")
    args = ap.parse_args()

    orch = Orchestrator(Path(registry_path_default()))
    include = [a.strip() for a in (args.agents or '').split(',') if a.strip()]
    count = register_agents(
        bus=orch.bus,
        registry=orch.registry,
        agents_root=Path("AGENTS").resolve(),
        include_ids=include or None,
    )
    print(f"Registered {count} L3 subscribers (agent.runtime.json)")

    env = orch.run_stage(
        name=f"{args.topic}-stage",
        topic=args.topic,
        payload={"demo": True},
        budget_ms=2000,
    )
    print(env.to_json())


if __name__ == "__main__":
    main()

