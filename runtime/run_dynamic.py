#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

from runtime.layer1.orchestrator import Orchestrator, registry_path_default
from runtime.layer2.auto_register import auto_register_by_tags


def main() -> None:
    ap = argparse.ArgumentParser(description="Run hybrid workflow with dynamic L3 registration")
    ap.add_argument("topic", choices=[
        "gtm.content",
        "security.compliance",
        "people.personnel",
        "legal.contract",
        "ops.project",
        "sales.pipeline"
    ])
    ap.add_argument("--include-tags", help="Comma-separated tags to include (optional)")
    args = ap.parse_args()

    orch = Orchestrator(Path(registry_path_default()))
    include = [t.strip() for t in (args.include_tags or '').split(',') if t.strip()]
    count = auto_register_by_tags(
        bus=orch.bus,
        registry=orch.registry,
        topic_map_path=Path("runtime/layer2/topic_map.json").resolve(),
        include_tags=include or None,
    )
    print(f"Registered {count} dynamic subscribers from registry")

    env = orch.run_stage(
        name=f"{args.topic}-stage",
        topic=args.topic,
        payload={"demo": True},
        budget_ms=2000,
        expected_keys=None,
    )
    print(env.to_json())


if __name__ == "__main__":
    main()

