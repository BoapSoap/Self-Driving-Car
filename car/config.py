"""Central hardware configuration.

The built-in values are simulation-only examples. They are deliberately marked
unverified and MUST NOT be treated as measured hardware calibration.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


class ConfigurationError(ValueError):
    """Configuration is internally inconsistent or unsafe."""


@dataclass
class PCA9685Config:
    address: int = 0x40
    frequency_hz: float = 50.0
    min_pulse_us: int = 500
    max_pulse_us: int = 2500


@dataclass
class ServoConfig:
    channel: int
    center_us: int
    min_us: int
    max_us: int
    inverted: bool = False
    trim_us: int = 0
    calibrated: bool = False


@dataclass
class ESCConfig:
    channel: int
    safe_us: int
    arm_us: int
    minimum_moving_us: int
    test_max_us: int
    calibrated_max_us: int
    inverted: bool = False
    reverse_channel: int | None = None
    reverse_us: int | None = None
    calibrated: bool = False


@dataclass
class DynamicsConfig:
    throttle_accel_per_s: float = 0.5
    throttle_decel_per_s: float = 1.25
    steering_out_per_s: float = 2.5
    steering_recenter_per_s: float = 3.333333
    control_hz: float = 50.0
    key_expiry_s: float = 0.18


@dataclass
class CarConfig:
    pca9685: PCA9685Config
    steering: dict[str, ServoConfig]
    motors: dict[str, ESCConfig]
    dynamics: DynamicsConfig = field(default_factory=DynamicsConfig)
    arming_duration_s: float = 2.0
    watchdog_timeout_s: float = 0.300
    reverse_physically_verified: bool = False
    hardware_configuration_verified: bool = False
    notes: list[str] = field(default_factory=list)

    def validate(self, *, for_real_motor_test: bool = False) -> None:
        errors: list[str] = []
        if not 1 <= self.pca9685.frequency_hz <= 1600:
            errors.append("PCA9685 frequency must be between 1 and 1600 Hz")
        if not 0 < self.watchdog_timeout_s <= 0.300:
            errors.append("watchdog_timeout_s must be positive and no greater than 0.300")
        if self.arming_duration_s < 0:
            errors.append("arming_duration_s cannot be negative")

        used: dict[int, str] = {}
        for name, servo in self.steering.items():
            _channel_error(servo.channel, f"steering.{name}", errors, used)
            if not servo.min_us <= servo.center_us <= servo.max_us:
                errors.append(f"steering.{name}: require min_us <= center_us <= max_us")
            if servo.min_us + servo.trim_us < self.pca9685.min_pulse_us:
                errors.append(f"steering.{name}: trimmed minimum is below backend limit")
            if servo.max_us + servo.trim_us > self.pca9685.max_pulse_us:
                errors.append(f"steering.{name}: trimmed maximum is above backend limit")

        for name, esc in self.motors.items():
            _channel_error(esc.channel, f"motors.{name}", errors, used)
            values = (
                esc.safe_us,
                esc.arm_us,
                esc.minimum_moving_us,
                esc.test_max_us,
                esc.calibrated_max_us,
            )
            if any(v < self.pca9685.min_pulse_us or v > self.pca9685.max_pulse_us for v in values):
                errors.append(f"motors.{name}: ESC pulse is outside backend limits")
            if esc.test_max_us > esc.calibrated_max_us:
                errors.append(f"motors.{name}: test_max_us exceeds calibrated_max_us")
            if esc.minimum_moving_us > esc.test_max_us:
                errors.append(f"motors.{name}: minimum_moving_us exceeds test_max_us")
            if esc.reverse_channel is not None:
                _channel_error(esc.reverse_channel, f"motors.{name}.reverse", errors, used)
            if self.reverse_physically_verified and (
                esc.reverse_channel is None or esc.reverse_us is None
            ):
                errors.append(f"motors.{name}: verified reverse requires channel and pulse")

        d = self.dynamics
        if any(
            rate <= 0
            for rate in (
                d.throttle_accel_per_s,
                d.throttle_decel_per_s,
                d.steering_out_per_s,
                d.steering_recenter_per_s,
                d.control_hz,
            )
        ):
            errors.append("all dynamics rates and control_hz must be positive")
        if d.key_expiry_s <= 0 or d.key_expiry_s >= self.watchdog_timeout_s:
            errors.append("key_expiry_s must be positive and shorter than watchdog timeout")
        if for_real_motor_test:
            if not self.hardware_configuration_verified:
                errors.append("hardware_configuration_verified must be true")
            for name, servo in self.steering.items():
                if not servo.calibrated:
                    errors.append(f"steering.{name}: calibrated must be true")
            for name, esc in self.motors.items():
                if not esc.calibrated:
                    errors.append(f"motors.{name}: calibrated must be true")
        if errors:
            raise ConfigurationError("\n".join(errors))


def _channel_error(channel: int, label: str, errors: list[str], used: dict[int, str]) -> None:
    if not 0 <= channel <= 15:
        errors.append(f"{label}: channel {channel} is outside 0..15")
    if channel in used:
        errors.append(f"{label}: channel {channel} overlaps {used[channel]}")
    else:
        used[channel] = label


def simulation_config() -> CarConfig:
    """Return an explicitly unverified configuration for dry-run and tests only."""
    warning = (
        "SIMULATION VALUES ONLY: channel assignments and pulse widths below are "
        "not measured hardware values. Replace every value and mark calibration."
    )
    return CarConfig(
        pca9685=PCA9685Config(),
        steering={
            "left": ServoConfig(0, 1500, 1200, 1800),
            "right": ServoConfig(1, 1500, 1200, 1800, inverted=True),
        },
        motors={
            "front_left": ESCConfig(2, 1000, 1000, 1100, 1150, 2000),
            "front_right": ESCConfig(3, 1000, 1000, 1100, 1150, 2000),
            "rear_left": ESCConfig(4, 1000, 1000, 1100, 1150, 2000),
            "rear_right": ESCConfig(5, 1000, 1000, 1100, 1150, 2000),
        },
        hardware_configuration_verified=False,
        notes=[warning],
    )


def load_config(path: str | Path | None = None) -> CarConfig:
    """Load JSON configuration, or simulation-only defaults when path is omitted."""
    if path is None:
        config = simulation_config()
    else:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        config = _from_dict(raw)
    config.validate()
    return config


def save_config_template(path: str | Path) -> None:
    Path(path).write_text(json.dumps(asdict(simulation_config()), indent=2), encoding="utf-8")


def _from_dict(raw: dict[str, Any]) -> CarConfig:
    return CarConfig(
        pca9685=PCA9685Config(**raw["pca9685"]),
        steering={k: ServoConfig(**v) for k, v in raw["steering"].items()},
        motors={k: ESCConfig(**v) for k, v in raw["motors"].items()},
        dynamics=DynamicsConfig(**raw.get("dynamics", {})),
        arming_duration_s=raw.get("arming_duration_s", 2.0),
        watchdog_timeout_s=raw.get("watchdog_timeout_s", 0.300),
        reverse_physically_verified=raw.get("reverse_physically_verified", False),
        hardware_configuration_verified=raw.get("hardware_configuration_verified", False),
        notes=raw.get("notes", []),
    )
