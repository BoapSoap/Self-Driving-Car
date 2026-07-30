"""Independent calibrated steering-servo mapping."""

from __future__ import annotations

from dataclasses import dataclass

from car.config import ServoConfig
from .pwm_backend import PWMBackend


@dataclass(frozen=True)
class SteeringOutput:
    normalized: float
    pulse_us: float


class SteeringServo:
    def __init__(self, backend: PWMBackend, config: ServoConfig):
        self.backend = backend
        self.config = config
        self.last_output: SteeringOutput | None = None

    def pulse_for(self, command: float) -> float:
        command = max(-1.0, min(1.0, float(command)))
        mapped = -command if self.config.inverted else command
        center = self.config.center_us + self.config.trim_us
        endpoint = (
            self.config.max_us + self.config.trim_us
            if mapped >= 0
            else self.config.min_us + self.config.trim_us
        )
        pulse = center + abs(mapped) * (endpoint - center)
        return max(
            self.config.min_us + self.config.trim_us,
            min(self.config.max_us + self.config.trim_us, pulse),
        )

    def set(self, command: float) -> SteeringOutput:
        normalized = max(-1.0, min(1.0, float(command)))
        pulse = self.pulse_for(normalized)
        self.backend.set_pulse_us(self.config.channel, pulse)
        self.last_output = SteeringOutput(normalized, pulse)
        return self.last_output

    def center(self) -> SteeringOutput:
        return self.set(0.0)
