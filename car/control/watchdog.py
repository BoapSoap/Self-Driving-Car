"""Monotonic input watchdog."""

from __future__ import annotations

import time
from typing import Callable


class CommandWatchdog:
    def __init__(self, timeout_s: float = 0.300, clock: Callable[[], float] = time.monotonic):
        if not 0 < timeout_s <= 0.300:
            raise ValueError("watchdog timeout must be in (0, 0.300] seconds")
        self.timeout_s = timeout_s
        self.clock = clock
        self.last_refresh: float | None = None

    def refresh(self) -> None:
        self.last_refresh = self.clock()

    @property
    def expired(self) -> bool:
        return self.last_refresh is None or self.clock() - self.last_refresh > self.timeout_s
