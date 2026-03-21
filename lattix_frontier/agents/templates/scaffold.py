"""Agent scaffolding implementation."""

from __future__ import annotations

import shutil
from pathlib import Path


def scaffold_agent(name: str, destination: Path) -> Path:
    """Create a new agent scaffold from the built-in template."""

    source = Path(__file__).parent / "agent_template"
    output_dir = destination / name
    if output_dir.exists():
        msg = f"Agent scaffold already exists: {output_dir}"
        raise FileExistsError(msg)
    shutil.copytree(source, output_dir)
    config_path = output_dir / "config.json"
    config_text = config_path.read_text(encoding="utf-8").replace("template-agent", name)
    config_path.write_text(config_text, encoding="utf-8")
    return output_dir
