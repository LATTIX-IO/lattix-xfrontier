#!/usr/bin/env python3
"""
Bulk update agent configs across AGENTS/*:
- owners, tags (replace or append)
- model_defaults: temperature, top_p, max_tokens, provider, model

Usage examples:
  python3 scripts/bulk_update_agents.py \
    --owners owner@example.com,team@example.com \
    --tags core,prod \
    --temperature 0.2 --top-p 0.95 --max-tokens 4096

  # Append instead of replace for owners/tags
  python3 scripts/bulk_update_agents.py --owners a@b --append-owners
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from typing import List

ROOT = Path(os.getcwd())
AGENTS_DIR = ROOT / "AGENTS"


def parse_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [s.strip() for s in value.split(",") if s.strip()]


def main() -> None:
    ap = argparse.ArgumentParser(description="Bulk update agent configs")
    ap.add_argument("--owners", help="Comma-separated owners (emails/handles)")
    ap.add_argument("--tags", help="Comma-separated tags")
    ap.add_argument("--append-owners", action="store_true", help="Append owners instead of replace")
    ap.add_argument("--append-tags", action="store_true", help="Append tags instead of replace")

    ap.add_argument("--provider", help="Model provider (e.g., openai)")
    ap.add_argument("--model", help="Model name (e.g., gpt-5)")
    ap.add_argument("--temperature", type=float, help="Sampling temperature")
    ap.add_argument("--top-p", dest="top_p", type=float, help="Nucleus sampling top_p")
    ap.add_argument("--max-tokens", dest="max_tokens", type=int, help="Max output tokens")

    args = ap.parse_args()

    owners = parse_csv(args.owners)
    tags = parse_csv(args.tags)

    changes = []
    for d in sorted(p for p in AGENTS_DIR.iterdir() if p.is_dir()):
        if d.name == "REGISTRY":
            continue
        cfg_path = d / "agent.config.json"
        if not cfg_path.exists():
            continue

        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        changed = False

        # Owners
        if owners:
            if args.append_owners:
                existing = cfg.get("owners", [])
                merged = list(dict.fromkeys(existing + owners))  # dedupe preserve order
                if merged != existing:
                    cfg["owners"] = merged
                    changed = True
            else:
                if cfg.get("owners") != owners:
                    cfg["owners"] = owners
                    changed = True

        # Tags
        if tags:
            if args.append_tags:
                existing = cfg.get("tags", [])
                merged = list(dict.fromkeys(existing + tags))
                if merged != existing:
                    cfg["tags"] = merged
                    changed = True
            else:
                if cfg.get("tags") != tags:
                    cfg["tags"] = tags
                    changed = True

        # Model defaults
        md = cfg.setdefault("model_defaults", {})
        for key, val in (
            ("provider", args.provider),
            ("model", args.model),
            ("temperature", args.temperature),
            ("top_p", args.top_p),
            ("max_tokens", args.max_tokens),
        ):
            if val is not None and md.get(key) != val:
                md[key] = val
                changed = True

        if changed:
            cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
            changes.append(d.name)

    print(f"Updated {len(changes)} agents")
    for name in changes:
        print(f"- {name}")


if __name__ == "__main__":
    main()

