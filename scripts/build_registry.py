#!/usr/bin/env python3
"""
Build agents registry by scanning AGENTS/* directories.
- Prefers agent.config.json when present
- Falls back to url-manifest-*.json
- Detects system-prompt.md if present
Writes AGENTS/REGISTRY/agents.registry.json
"""
from __future__ import annotations
import json
import os
from pathlib import Path

ROOT = Path(os.getcwd())
AGENTS_DIR = ROOT / "AGENTS"
REGISTRY_DIR = AGENTS_DIR / "REGISTRY"
OUT = REGISTRY_DIR / "agents.registry.json"


def read_json_maybe(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def slug_to_name(slug: str) -> str:
    return slug.replace("-", " ").title()


def main() -> None:
    if not AGENTS_DIR.exists():
        raise SystemExit("AGENTS/ not found")
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

    entries = []
    for d in sorted(p for p in AGENTS_DIR.iterdir() if p.is_dir()):
        if d.name.lower() == "registry":
            continue

        config_path = d / "agent.config.json"
        prompt_path = d / "system-prompt.md"
        files = list(d.iterdir())
        manifest = next((f for f in files if f.name.startswith("url-manifest-") or f.name.startswith("url-mapping-")), None)

        cfg = read_json_maybe(config_path)

        base = {
            "id": (cfg or {}).get("id", d.name),
            "name": (cfg or {}).get("name", slug_to_name(d.name)),
            "status": (cfg or {}).get("status", "draft"),
            "version": (cfg or {}).get("version", "0.1.0"),
            "prompt_file": str(prompt_path.relative_to(AGENTS_DIR)) if prompt_path.exists() else None,
            "url_manifest": str(manifest.relative_to(AGENTS_DIR)) if manifest else None,
            "owners": (cfg or {}).get("owners", []),
            "tags": (cfg or {}).get("tags", []),
            "model_defaults": (cfg or {}).get("model_defaults", None),
        }
        entries.append(base)

    from datetime import datetime, timezone
    out = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agents": sorted(entries, key=lambda x: x["id"]),
    }

    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
