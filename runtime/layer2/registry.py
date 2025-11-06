from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class AgentsRegistry:
    def __init__(self, registry_path: Path) -> None:
        self._path = registry_path
        self._data: Dict[str, Any] = {}
        self._index: Dict[str, Dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        self._data = json.loads(self._path.read_text(encoding="utf-8"))
        self._index = {a["id"]: a for a in self._data.get("agents", [])}

    def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self._index.get(agent_id)

    def all(self) -> List[Dict[str, Any]]:
        return list(self._index.values())

    def by_tag(self, tag: str) -> List[Dict[str, Any]]:
        return [a for a in self._index.values() if tag in (a.get("tags") or [])]

