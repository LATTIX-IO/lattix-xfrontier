#!/usr/bin/env python3
from __future__ import annotations
import argparse
import shutil
from pathlib import Path


ROOT = Path.cwd()
AGENTS = ROOT / "AGENTS"
TEMPLATE = ROOT / "services" / "AGENT_SERVICE_TEMPLATE"
SERVICES = ROOT / "services"


def scaffold(agent_id: str) -> Path:
    src = TEMPLATE
    dst = SERVICES / agent_id
    dst.mkdir(parents=True, exist_ok=True)
    # copytree while allowing existing dirs
    for p in src.rglob("*"):
        rel = p.relative_to(src)
        target = dst / rel
        if p.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            if not target.exists():
                if p.name == "README.md":
                    content = p.read_text(encoding="utf-8").replace("agent-service", agent_id)
                    target.write_text(content, encoding="utf-8")
                else:
                    shutil.copy2(p, target)
    return dst


def main() -> None:
    ap = argparse.ArgumentParser(description="Scaffold a containerized service for an agent")
    ap.add_argument("agent_id", help="Agent folder name under AGENTS/")
    args = ap.parse_args()
    agent_dir = AGENTS / args.agent_id
    if not agent_dir.exists():
        raise SystemExit(f"Agent not found: {args.agent_id}")
    out = scaffold(args.agent_id)
    print(f"Service scaffolded at {out}")


if __name__ == "__main__":
    main()

