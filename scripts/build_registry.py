"""Build a JSON representation of the built-in agent registry."""

from __future__ import annotations

import json
from pathlib import Path

from lattix_frontier.agents.registry import build_default_registry


def main() -> None:
    records = [record.model_dump() for record in build_default_registry().list_agents()]
    output_path = Path("agents.registry.json")
    output_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(output_path)  # noqa: T201


if __name__ == "__main__":
    main()
