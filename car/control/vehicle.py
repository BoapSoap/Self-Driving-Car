"""High-level vehicle interface shared by terminal, future controller, and AI."""

from __future__ import annotations

import time
from dataclasses import dataclass

from car.config import CarConfig
from car.hardware.esc import ESC, ESCState
from car.hardware.pwm_backend import PWMBackend
from car.hardware.steering import SteeringServo


@dataclass(frozen=True)
class VehicleSnapshot:
    steering: float
    throttle: float
    drive_state: str
    pulses_us: dict[str, float]
    emergency_stopped: bool


class Vehicle:
    def __init__(self, backend: PWMBackend, config: CarConfig):
        config.validate()
        self.backend = backend
        self.config = config
        self.steering = {
            name: SteeringServo(backend, servo) for name, servo in config.steering.items()
        }
        self.motors = {
            name: ESC(backend, esc, reverse_enabled=False) for name, esc in config.motors.items()
        }
        self.emergency_stopped = False
        self._closed = False
        try:
            self.safe_startup()
        except BaseException:
            self._best_effort_safe()
            backend.shutdown()
            self._closed = True
            raise

    def safe_startup(self) -> None:
        for esc in self.motors.values():
            esc.safe()
        for servo in self.steering.values():
            servo.center()

    def arm(self) -> None:
        if self.emergency_stopped:
            raise RuntimeError("cannot arm after emergency stop")
        try:
            for esc in self.motors.values():
                esc.begin_arming()
            time.sleep(self.config.arming_duration_s)
            for esc in self.motors.values():
                esc.finish_arming()
        except BaseException:
            self.emergency_stop(fault=True)
            raise

    def set_steering(self, command: float) -> None:
        for servo in self.steering.values():
            servo.set(command)

    def set_throttle(self, command: float) -> None:
        if self.emergency_stopped:
            raise RuntimeError("vehicle is emergency-stopped")
        for esc in self.motors.values():
            esc.set_throttle(command)

    def emergency_stop(self, *, fault: bool = False) -> None:
        self.emergency_stopped = True
        for esc in self.motors.values():
            try:
                esc.fault() if fault else esc.safe()
            except Exception:
                pass

    def snapshot(self) -> VehicleSnapshot:
        pulses: dict[str, float] = {}
        for name, servo in self.steering.items():
            if servo.last_output:
                pulses[f"steering.{name}"] = servo.last_output.pulse_us
        for name, esc in self.motors.items():
            if esc.last_output:
                pulses[f"motor.{name}"] = esc.last_output.pulse_us
        steering = next(
            (s.last_output.normalized for s in self.steering.values() if s.last_output), 0.0
        )
        throttle = next(
            (e.last_output.normalized for e in self.motors.values() if e.last_output), 0.0
        )
        states = {esc.state for esc in self.motors.values()}
        state = next(iter(states)).value if len(states) == 1 else "mixed"
        return VehicleSnapshot(steering, throttle, state, pulses, self.emergency_stopped)

    def _best_effort_safe(self) -> None:
        for esc in self.motors.values():
            try:
                esc.safe()
            except Exception:
                pass
        for servo in self.steering.values():
            try:
                servo.center()
            except Exception:
                pass

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._best_effort_safe()
        finally:
            self.backend.shutdown()
            self._closed = True

    def __enter__(self) -> "Vehicle":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
