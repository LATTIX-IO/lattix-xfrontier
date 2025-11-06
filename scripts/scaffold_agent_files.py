#!/usr/bin/env python3
"""
Scaffold per-agent files:
- system-prompt.md (from template) if missing
- agent.config.json (minimal) if missing
- README.md (from template) if missing
"""
from __future__ import annotations
import json
import os
from pathlib import Path

ROOT = Path(os.getcwd())
AGENTS_DIR = ROOT / "AGENTS"
TEMPLATES_DIR = ROOT / "TEMPLATES"
TEMPLATE_PROMPT = TEMPLATES_DIR / "SYSTEM_PROMPT_TEMPLATE.md"
TEMPLATE_README = TEMPLATES_DIR / "AGENT_README_TEMPLATE.md"


def slug_to_name(slug: str) -> str:
    return slug.replace("-", " ").title()


def ensure_file(path: Path, content: str) -> bool:
    if not path.exists():
        path.write_text(content, encoding="utf-8")
        return True
    return False


def main() -> None:
    prompt_tpl = TEMPLATE_PROMPT.read_text(encoding="utf-8") if TEMPLATE_PROMPT.exists() else "# System Prompt\n"
    readme_tpl = TEMPLATE_README.read_text(encoding="utf-8") if TEMPLATE_README.exists() else "# Agent\n"

    created = []
    for d in sorted(p for p in AGENTS_DIR.iterdir() if p.is_dir()):
        if d.name == "REGISTRY":
            continue

        files = [p.name for p in d.iterdir() if p.is_file()]
        manifest = next((f for f in files if f.startswith("url-manifest-") or f.startswith("url-mapping-")), "")
        name = slug_to_name(d.name)

        prompt_path = d / "system-prompt.md"
        config_path = d / "agent.config.json"
        readme_path = d / "README.md"

        c = {"id": d.name, "prompt": False, "config": False, "readme": False}

        c["prompt"] = ensure_file(
            prompt_path,
            f"<!-- Fill in per {name}. See TEMPLATES/SYSTEM_PROMPT_TEMPLATE.md -->\n\n" + prompt_tpl,
        )

        if not config_path.exists():
            cfg = {
                "schema_version": "1.0.0",
                "id": d.name,
                "name": name,
                "description": "",
                "version": "0.1.0",
                "status": "draft",
                "owners": [],
                "tags": [],
                "capabilities": [],
                "prompt_file": "system-prompt.md",
                "url_manifest": manifest,
                "model_defaults": {"provider": "openai", "model": "gpt-5", "temperature": 0.2},
            }
            config_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
            c["config"] = True

        if not readme_path.exists():
            readme_content = readme_tpl.replace("<Agent Name>", name)
            readme_path.write_text(readme_content, encoding="utf-8")
            c["readme"] = True

        if any([c["prompt"], c["config"], c["readme"]]):
            created.append(c)

    print(f"Scaffolded {len(created)} agents")
    for r in created:
        print(f"- {r['id']}: prompt={r['prompt']} config={r['config']} readme={r['readme']}")


if __name__ == "__main__":
    main()
