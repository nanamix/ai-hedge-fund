from __future__ import annotations

import hashlib
import json
from pathlib import Path


class FlowStateStore:
    def __init__(self, path: Path):
        self.path = path

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _message_hash(self, message: str) -> str:
        return hashlib.sha256(message.encode("utf-8")).hexdigest()

    def is_duplicate(self, slot: str, message: str) -> bool:
        state = self._load()
        return state.get(slot, {}).get("message_hash") == self._message_hash(message)

    def record(self, slot: str, message: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        state = self._load()
        state[slot] = {"message_hash": self._message_hash(message)}
        self.path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
