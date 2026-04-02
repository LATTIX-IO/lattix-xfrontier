#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

WORKERS_ROOT = Path(__file__).resolve().parents[1]
if str(WORKERS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKERS_ROOT))

from runtime.layer1.orchestrator import Orchestrator, registry_path_default
from runtime.paths import topic_endpoints_map_path


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Dispatch an Envelope to remote agent services by topic"
    )
    ap.add_argument("topic", help="Topic (e.g., gtm.content)")
    ap.add_argument("--payload", help="JSON payload string (default: {})", default="{}")
    ap.add_argument(
        "--map",
        dest="map_path",
        help="Path to topic_endpoints JSON",
        default=str(topic_endpoints_map_path()),
    )
    args = ap.parse_args()

    orch = Orchestrator(Path(registry_path_default()))
    env = orch.run_stage(
        name=f"{args.topic}-remote",
        topic=args.topic,
        payload=json.loads(args.payload),
        dispatch_mode="remote",
        remote_map_path=Path(args.map_path).resolve(),
    )
    remote_responses = (
        env.payload.get("remote_responses") if isinstance(env.payload, dict) else None
    )
    resp = remote_responses[-1] if isinstance(remote_responses, list) and remote_responses else None
    print(json.dumps({"request": json.loads(env.to_json()), "response": resp}, indent=2))


if __name__ == "__main__":
    main()
