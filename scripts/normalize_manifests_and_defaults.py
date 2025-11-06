#!/usr/bin/env python3
"""
Normalize agent folders by:
- Renaming files from url-mapping-* to url-manifest-*
- Updating agent.config.json url_manifest to the new name
- Setting org-wide model_defaults to provider=openai, model=gpt-5
"""
from __future__ import annotations
import json
import os
from pathlib import Path

ROOT = Path(os.getcwd())
AGENTS_DIR = ROOT / "AGENTS"


def main() -> None:
    changes = []
    for d in sorted(p for p in AGENTS_DIR.iterdir() if p.is_dir()):
        if d.name == "REGISTRY":
            continue
        files = [p for p in d.iterdir() if p.is_file()]

        # Rename url-mapping-* -> url-manifest-*
        for f in files:
            name = f.name
            if name.startswith("url-mapping-") and name.endswith(".json"):
                dst = f.with_name(name.replace("url-mapping-", "url-manifest-"))
                f.rename(dst)
                changes.append({"agent": d.name, "type": "rename", "from": name, "to": dst.name})

        cfg_path = d / "agent.config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            urlm = cfg.get("url_manifest")
            if isinstance(urlm, str) and urlm.startswith("url-mapping-"):
                cfg["url_manifest"] = urlm.replace("url-mapping-", "url-manifest-")

            md = cfg.setdefault("model_defaults", {})
            md["provider"] = "openai"
            md["model"] = "gpt-5"

            cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
            changes.append({"agent": d.name, "type": "update-config"})

    print(f"Normalized {len(changes)} changes")
    for c in changes:
        if c["type"] == "rename":
            print(f"- {c['agent']}: {c['from']} -> {c['to']}")
        elif c["type"] == "update-config":
            print(f"- {c['agent']}: agent.config.json updated")


if __name__ == "__main__":
    main()

