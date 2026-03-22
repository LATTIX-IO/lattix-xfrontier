#!/usr/bin/env python3
from __future__ import annotations
import argparse
import sys
from pathlib import Path

WORKERS_ROOT = Path(__file__).resolve().parents[1]
if str(WORKERS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKERS_ROOT))

from runtime.layer1.orchestrator import Orchestrator, registry_path_default
from runtime.examples.demo_subscribers import register_demo_subscribers


def main() -> None:
    ap = argparse.ArgumentParser(description="Run demo hybrid workflows")
    ap.add_argument(
        "workflow",
        choices=["gtm", "security", "personnel", "contract", "project", "sales"],
        help="Which demo workflow to run",
    )
    args = ap.parse_args()

    orch = Orchestrator(Path(registry_path_default()))
    register_demo_subscribers(orch.bus)

    if args.workflow == "gtm":
        env = orch.run_stage(
            name="gtm-content",
            topic="gtm.content",
            payload={"brief": "Launch announcement draft"},
            budget_ms=2000,
        )
    elif args.workflow == "security":
        env = orch.run_stage(
            name="security-compliance",
            topic="security.compliance",
            payload={"system": "New SSP/SAR for Product X"},
            budget_ms=3000,
        )
    elif args.workflow == "personnel":
        env = orch.run_stage(
            name="personnel-actions",
            topic="people.personnel",
            payload={"employee": {"name": "Alex", "action": "onboard"}},
            budget_ms=3000,
        )
    elif args.workflow == "contract":
        env = orch.run_stage(
            name="contract-review",
            topic="legal.contract",
            payload={"contract": {"type": "msa", "counterparty": "Acme"}},
            budget_ms=3000,
        )
    elif args.workflow == "project":
        env = orch.run_stage(
            name="project-initiation",
            topic="ops.project",
            payload={"project": {"name": "Phoenix", "sponsor": "CTO"}},
            budget_ms=3000,
        )
    else:  # sales
        env = orch.run_stage(
            name="sales-process",
            topic="sales.pipeline",
            payload={"lead": {"company": "Globex", "size": "mid"}},
            budget_ms=3000,
        )

    print(env.to_json())


if __name__ == "__main__":
    main()
