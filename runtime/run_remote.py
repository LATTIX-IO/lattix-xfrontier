#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path

from runtime.layer1.orchestrator import Orchestrator, registry_path_default
from runtime.network.dispatcher import TopicDispatcher


def main() -> None:
    ap = argparse.ArgumentParser(description="Dispatch an Envelope to remote agent services by topic")
    ap.add_argument("topic", help="Topic (e.g., gtm.content)")
    ap.add_argument("--payload", help="JSON payload string (default: {})", default="{}")
    ap.add_argument("--map", dest="map_path", help="Path to topic_endpoints JSON", default="runtime/network/topic_endpoints.example.json")
    args = ap.parse_args()

    orch = Orchestrator(Path(registry_path_default()))
    env = orch.run_stage(name=f"{args.topic}-remote", topic=args.topic, payload=json.loads(args.payload))

    dispatcher = TopicDispatcher(Path(args.map_path))
    resp = dispatcher.dispatch(args.topic, env)
    print(json.dumps({"request": json.loads(env.to_json()), "response": resp}, indent=2))


if __name__ == "__main__":
    main()

