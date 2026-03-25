#!/usr/bin/env python3
"""Public bootstrap that fetches the packaged Frontier installer if needed."""

from __future__ import annotations

import importlib
import io
import os
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.request import urlopen
import zipfile

DEFAULT_ARCHIVE_URL = "https://github.com/LATTIX-IO/lattix-xfrontier/archive/refs/heads/main.zip"


def _download_repo_archive(target_dir: Path) -> Path:
    archive_url = os.environ.get("FRONTIER_ARCHIVE_URL", DEFAULT_ARCHIVE_URL)
    with urlopen(archive_url) as response:  # noqa: S310 - public installer fetch by design.
        archive_bytes = response.read()
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        archive.extractall(target_dir)
    extracted_roots = [path for path in target_dir.iterdir() if path.is_dir()]
    if not extracted_roots:
        raise SystemExit("Downloaded installer archive did not contain a repository directory.")
    return extracted_roots[0]


def _run_packaged_installer(repo_root: Path) -> None:
    sys.path.insert(0, str(repo_root))
    importlib.invalidate_caches()
    module = importlib.import_module("frontier_tooling.installer")
    module.main()


def main() -> None:
    cwd = Path.cwd()
    packaged = cwd / "frontier_tooling" / "installer.py"
    if packaged.exists():
        _run_packaged_installer(cwd)
        return
    temp_root = Path(tempfile.mkdtemp(prefix="frontier-public-installer-"))
    try:
        repo_root = _download_repo_archive(temp_root)
        packaged = repo_root / "frontier_tooling" / "installer.py"
        if not packaged.exists():
            raise SystemExit("The downloaded archive did not include frontier_tooling/installer.py")
        os.chdir(repo_root)
        _run_packaged_installer(repo_root)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    main()

