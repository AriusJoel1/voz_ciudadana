from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

from .domain import Initiative


class InitiativeRepository:
    def list(self) -> List[Initiative]:
        raise NotImplementedError

    def get(self, initiative_id: str) -> Optional[Initiative]:
        raise NotImplementedError

    def save(self, initiative: Initiative) -> Initiative:
        raise NotImplementedError

    def delete_all(self) -> None:
        raise NotImplementedError


class JsonFileInitiativeRepository(InitiativeRepository):
    def __init__(self, storage_path: str | Path):
        self.path = Path(storage_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        if not self.path.exists():
            self._write_all([])

    def _read_all(self) -> List[dict]:
        with self._lock:
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return []

    def _write_all(self, data: List[dict]) -> None:
        with self._lock:
            self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def list(self) -> List[Initiative]:
        return [Initiative.from_dict(item) for item in self._read_all()]

    def get(self, initiative_id: str) -> Optional[Initiative]:
        for initiative in self.list():
            if initiative.id == initiative_id:
                return initiative
        return None

    def save(self, initiative: Initiative) -> Initiative:
        items = self._read_all()
        replacement = initiative.to_dict()
        updated = False
        for idx, item in enumerate(items):
            if item.get("id") == initiative.id:
                items[idx] = replacement
                updated = True
                break
        if not updated:
            items.append(replacement)
        self._write_all(items)
        return initiative

    def delete_all(self) -> None:
        self._write_all([])
