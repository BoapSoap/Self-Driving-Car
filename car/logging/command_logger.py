"""Best-effort JSONL logging designed for later frame synchronization."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class CommandLogger:
    def __init__(self, path: str | Path | None):
        self._file = Path(path).open("a", encoding="utf-8") if path else None

    def log(self, **record: Any) -> bool:
        record.setdefault("monotonic_timestamp_ns", time.monotonic_ns())
        record.setdefault("wall_clock_timestamp", time.time())
        record.setdefault("camera_frame_id", None)
        if self._file is None:
            return True
        try:
            self._file.write(json.dumps(record, separators=(",", ":")) + "\n")
            self._file.flush()
            return True
        except Exception:
            return False

    def close(self) -> None:
        if self._file:
            try:
                self._file.close()
            except Exception:
                pass

    def __enter__(self) -> "CommandLogger":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
