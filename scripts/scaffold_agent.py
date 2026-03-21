"""CLI helper to scaffold a Frontier agent."""

from __future__ import annotations

import argparse
from pathlib import Path

from lattix_frontier.agents.templates.scaffold import scaffold_agent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--destination", default="generated-agents")
    args = parser.parse_args()
    created = scaffold_agent(args.name, Path(args.destination))
    print(created)  # noqa: T201


if __name__ == "__main__":
    main()
