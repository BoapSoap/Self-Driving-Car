"""No-I/O backend for development and safety testing."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .pwm_backend import PWMBackend, validate_pulse_us


@dataclass(frozen=True)
class OutputEvent:
    timestamp_ns: int
    channel: int
    pulse_us: float | None


class DryRunBackend(PWMBackend):
    def __init__(self, min_pulse_us: float = 500, max_pulse_us: float = 2500, *, echo: bool = True):
        self.min_pulse_us = min_pulse_us
        self.max_pulse_us = max_pulse_us
        self.echo = echo
        self.events: list[OutputEvent] = []
        self.outputs: dict[int, float | None] = {}
        self.is_shutdown = False

    def set_pulse_us(self, channel: int, pulse_us: float) -> None:
        if self.is_shutdown:
            raise RuntimeError("backend is shut down")
        if not 0 <= channel <= 15:
            raise ValueError("channel must be in 0..15")
        validate_pulse_us(pulse_us, self.min_pulse_us, self.max_pulse_us)
        self.outputs[channel] = pulse_us
        self.events.append(OutputEvent(time.monotonic_ns(), channel, pulse_us))
        if self.echo:
            print(f"DRY-RUN channel={channel} pulse_us={pulse_us:.1f}")

    def disable_channel(self, channel: int) -> None:
        self.outputs[channel] = None
        self.events.append(OutputEvent(time.monotonic_ns(), channel, None))
        if self.echo:
            print(f"DRY-RUN channel={channel} disabled")

    def shutdown(self) -> None:
        self.is_shutdown = True
        if self.echo:
            print("DRY-RUN backend shut down")
