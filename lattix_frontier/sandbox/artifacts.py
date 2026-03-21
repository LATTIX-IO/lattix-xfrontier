"""Workspace staging and artifact collection for sandboxed tool execution."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import tempfile


@dataclass(slots=True)
class WorkspaceLayout:
    """Directory layout for a single jailed tool execution."""

    root: Path
    input_dir: Path
    output_dir: Path
    temp_dir: Path


def create_workspace(root_dir: Path | None = None) -> WorkspaceLayout:
    """Create an isolated workspace tree for one execution."""

    base_dir = root_dir or Path(tempfile.mkdtemp(prefix="frontier-sandbox-"))
    base_dir.mkdir(parents=True, exist_ok=True)
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"
    temp_dir = base_dir / "tmp"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    return WorkspaceLayout(root=base_dir, input_dir=input_dir, output_dir=output_dir, temp_dir=temp_dir)


def cleanup_workspace(layout: WorkspaceLayout) -> None:
    """Delete a workspace tree when execution is complete."""

    shutil.rmtree(layout.root, ignore_errors=True)


def _is_under_allowed_root(path: Path, allowed_roots: list[str]) -> bool:
    resolved_path = path.resolve()
    for allowed_root in allowed_roots:
        try:
            resolved_root = Path(allowed_root).resolve()
        except OSError:
            continue
        if os.path.commonpath([str(resolved_path), str(resolved_root)]) == str(resolved_root):
            return True
    return False


def stage_inputs(layout: WorkspaceLayout, input_paths: list[str], allowed_roots: list[str]) -> dict[str, str]:
    """Copy allowlisted inputs into the jailed workspace."""

    staged: dict[str, str] = {}
    for raw_path in input_paths:
        source = Path(raw_path)
        if not source.exists():
            msg = f"Input path does not exist: {source}"
            raise FileNotFoundError(msg)
        if allowed_roots and not _is_under_allowed_root(source, allowed_roots):
            msg = f"Input path not allowed by sandbox policy: {source}"
            raise PermissionError(msg)
        destination = layout.input_dir / source.name
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)
        staged[source.name] = str(destination)
    return staged


def prepare_output_paths(layout: WorkspaceLayout, output_paths: list[str]) -> list[Path]:
    """Prepare relative output locations inside the jailed output directory."""

    prepared: list[Path] = []
    for output_path in output_paths:
        candidate = (layout.output_dir / output_path).resolve()
        if os.path.commonpath([str(candidate), str(layout.output_dir.resolve())]) != str(layout.output_dir.resolve()):
            msg = f"Output path escapes sandbox output directory: {output_path}"
            raise PermissionError(msg)
        candidate.parent.mkdir(parents=True, exist_ok=True)
        prepared.append(candidate)
    return prepared


def collect_outputs(layout: WorkspaceLayout) -> dict[str, str]:
    """Collect output artifact paths from the workspace."""

    outputs: dict[str, str] = {}
    for path in layout.output_dir.rglob("*"):
        if path.is_file():
            outputs[str(path.relative_to(layout.output_dir))] = str(path)
    return outputs
