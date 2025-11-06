#!/usr/bin/env python3
"""
Assign tags to agents based on functional classification/grouping.
This is a first-pass mapping derived from agent names; adjust as needed.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

ROOT = Path(os.getcwd())
AGENTS_DIR = ROOT / "AGENTS"


GROUPS = {
    # Leadership & Strategy
    "leadership": {
        "agents": [
            "ceo-strategy-agent",
            "chief-of-staff-agent",
            "cfo-agent",
            "strategic-operations-agent",
        ],
        "tags": ["leadership", "strategy"],
    },
    # Go-To-Market (GTM) & Brand
    "gtm": {
        "agents": [
            "marketing-agent",
            "sales-agent",
            "brand-strategy-agent",
            "website-content-agent",
            "social-media-agent",
            "blog-writer-agent",
            "media-gen-agent",
            "partnership-development-agent",
            "customer-insights-agent",
            "market-intelligence-agent",
            "customer-success-agent",
        ],
        "tags": ["gtm", "brand", "growth", "content"],
    },
    # Product, Engineering & Platform
    "engineering": {
        "agents": [
            "product-owner-agent",
            "technical-writer-agent",
            "developer-agent",
            "test-qa-automation-agent",
            "ai-architect-eng-agent",
            "data-architect-eng-agent",
            "uml-architect-agent",
            "orchestration-agent",
            "devops-platform-agent",
            "prompt-engineering-agent",
        ],
        "tags": ["product", "engineering", "platform", "architecture"],
    },
    # Security, Risk & Compliance
    "security_compliance": {
        "agents": [
            "ciso-agent",
            "iso27001-agent",
            "nist-csf-2.0-agent",
            "nist-80053-r5-agent",
            "cmmc-2.0-agent",
            "compliance-control-mapper",
            "privacy-officer-agent",
            "sar-builder-agent",
            "ssp-builder-agent",
            "threat-intelligence-agent",
            "incident-handler-agent",
            "threat-modeling-agent",
            "cis-agent",
            "government-contract-agent",
            "general-counsel-agent",
            "quality-compliance-agent",
        ],
        "tags": ["security", "risk", "compliance", "governance"],
    },
    # Operations & People
    "operations_people": {
        "agents": [
            "people-ops-agent",
            "personnel-agent",
            "learning-development-agent",
        ],
        "tags": ["operations", "people", "enablement"],
    },
    # Research & Funding
    "research_funding": {
        "agents": [
            "research-agent",
            "grants-rfp-agent",
            "fundraising-agent",
        ],
        "tags": ["research", "funding"],
    },
}


def mapping_for(agent_id: str) -> list[str]:
    tags: list[str] = []
    for group in GROUPS.values():
        if agent_id in group["agents"]:
            for t in group["tags"]:
                if t not in tags:
                    tags.append(t)
    if not tags:
        tags = ["uncategorized"]
    return tags


def main() -> None:
    updated = []
    for d in sorted(p for p in AGENTS_DIR.iterdir() if p.is_dir()):
        if d.name == "REGISTRY":
            continue
        cfg_path = d / "agent.config.json"
        if not cfg_path.exists():
            continue
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        new_tags = mapping_for(d.name)
        if cfg.get("tags") != new_tags:
            cfg["tags"] = new_tags
            cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
            updated.append((d.name, new_tags))

    print(f"Tagged {len(updated)} agents")
    for aid, tags in updated:
        print(f"- {aid}: {', '.join(tags)}")


if __name__ == "__main__":
    main()

