from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class EventLog:
    def __init__(self, path: Path | None) -> None:
        self.path = path
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: str, **fields: Any) -> None:
        if not self.path:
            return
        record = {"ts": time.time(), "event": event, **fields}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

