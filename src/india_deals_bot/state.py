from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


class DealState:
    def __init__(self, path: Path, retention_days: int) -> None:
        self.path = path
        self.cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        self._seen = self._load()

    def _load(self) -> dict[str, datetime]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            values = {
                key: datetime.fromisoformat(timestamp)
                for key, timestamp in payload.items()
            }
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise RuntimeError(f"Could not read state file {self.path}: {exc}") from exc
        return {key: timestamp for key, timestamp in values.items() if timestamp >= self.cutoff}

    def contains(self, key: str) -> bool:
        return key in self._seen

    def mark(self, key: str) -> None:
        self._seen[key] = datetime.now(UTC)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: timestamp.isoformat() for key, timestamp in self._seen.items()}
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)
