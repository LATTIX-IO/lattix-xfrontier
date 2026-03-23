from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
for candidate in (REPO_ROOT / "apps" / "backend", REPO_ROOT / "apps" / "workers"):
    path_value = str(candidate)
    if path_value not in sys.path:
        sys.path.insert(0, path_value)
