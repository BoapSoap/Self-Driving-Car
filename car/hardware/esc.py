"""Safety-oriented unidirectional aircraft ESC abstraction."""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass
from typing import Callable

from car.config import ESCConfig
from .pwm_backend import PWMBackend


class ESCState(enum.Enum):
    DISABLED = "disabled"
    SAFE = "safe"
    ARMING = "arming"
    ARMED = "armed"
    FORWARD = "forward"
    FAULT = "fault"


@dataclass(frozen=True)
class ESCOutput:
    normalized: float
    pulse_us: float
    state: ESCState


class ESC:
    def __init__(self, backend: PWMBackend, config: ESCConfig, *, reverse_enabled: bool = False):
        if reverse_enabled:
            raise ValueError("reverse is not implemented in this milestone")
        self.backend = backend
        self.config = config
        self.state = ESCState.DISABLED
        self.last_output: ESCOutput | None = None

    def safe(self) -> ESCOutput:
        self.backend.set_pulse_us(self.config.channel, self.config.safe_us)
        self.state = ESCState.SAFE
        self.last_output = ESCOutput(0.0, self.config.safe_us, self.state)
        return self.last_output

    def arm(self, duration_s: float, sleep: Callable[[float], None] = time.sleep) -> ESCOutput:
        if self.state not in (ESCState.SAFE, ESCState.DISABLED):
            raise RuntimeError(f"cannot arm from {self.state.value}")
        self.begin_arming()
        try:
            sleep(duration_s)
        except BaseException:
            self.fault()
            raise
        return self.finish_arming()

    def begin_arming(self) -> ESCOutput:
        if self.state not in (ESCState.SAFE, ESCState.DISABLED):
            raise RuntimeError(f"cannot arm from {self.state.value}")
        self.safe()
        self.state = ESCState.ARMING
        self.backend.set_pulse_us(self.config.channel, self.config.arm_us)
        self.last_output = ESCOutput(0.0, self.config.arm_us, self.state)
        return self.last_output

    def finish_arming(self) -> ESCOutput:
        if self.state is not ESCState.ARMING:
            raise RuntimeError(f"cannot finish arming from {self.state.value}")
        self.backend.set_pulse_us(self.config.channel, self.config.safe_us)
        self.state = ESCState.ARMED
        self.last_output = ESCOutput(0.0, self.config.safe_us, self.state)
        return self.last_output

    def set_throttle(self, throttle: float) -> ESCOutput:
        throttle = float(throttle)
        if throttle < 0:
            raise ValueError("negative throttle/reverse is disabled and unverified")
        if throttle > 1:
            raise ValueError("throttle must be in 0..1")
        if self.state not in (ESCState.ARMED, ESCState.FORWARD):
            raise RuntimeError("ESC rejects throttle until successfully armed")
        if throttle == 0:
            pulse = self.config.safe_us
            self.state = ESCState.ARMED
        else:
            pulse = self.config.minimum_moving_us + throttle * (
                self.config.test_max_us - self.config.minimum_moving_us
            )
            self.state = ESCState.FORWARD
        if self.config.inverted:
            pulse = self.config.safe_us - (pulse - self.config.safe_us)
        self.backend.set_pulse_us(self.config.channel, pulse)
        self.last_output = ESCOutput(throttle, pulse, self.state)
        return self.last_output

    def fault(self) -> ESCOutput:
        try:
            self.backend.set_pulse_us(self.config.channel, self.config.safe_us)
        finally:
            self.state = ESCState.FAULT
            self.last_output = ESCOutput(0.0, self.config.safe_us, self.state)
        return self.last_output

    def disable(self) -> None:
        self.safe()
        self.backend.disable_channel(self.config.channel)
        self.state = ESCState.DISABLED
