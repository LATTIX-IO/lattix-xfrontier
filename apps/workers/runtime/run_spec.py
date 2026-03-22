#!/usr/bin/env python3
from __future__ import annotations
import argparse
import sys
from pathlib import Path

WORKERS_ROOT = Path(__file__).resolve().parents[1]
if str(WORKERS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKERS_ROOT))

from runtime.layer1.workflow_engine import run_workflow_file


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a workflow from a JSON spec")
    ap.add_argument("spec", help="Path to workflow JSON file")
    args = ap.parse_args()
    out = run_workflow_file(Path(args.spec))
    print(out["last_env"])


if __name__ == "__main__":
    main()

