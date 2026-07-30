"""Replaceable pulse-width backend contract and shared validation."""

from __future__ import annotations

from abc import ABC, abstractmethod


class PWMError(RuntimeError):
    pass


def validate_pulse_us(pulse_us: float, minimum_us: float = 500, maximum_us: float = 2500) -> None:
    if not isinstance(pulse_us, (int, float)) or isinstance(pulse_us, bool):
        raise ValueError("pulse width must be numeric")
    if not minimum_us <= pulse_us <= maximum_us:
        raise ValueError(f"pulse width {pulse_us} us is outside {minimum_us}..{maximum_us} us")


def microseconds_to_duty_cycle(pulse_us: float, frequency_hz: float) -> int:
    validate_pulse_us(pulse_us, 0, 1_000_000)
    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be positive")
    period_us = 1_000_000.0 / frequency_hz
    if pulse_us > period_us:
        raise ValueError("pulse width cannot exceed PWM period")
    return min(0xFFFF, max(0, round((pulse_us / period_us) * 0xFFFF)))


class PWMBackend(ABC):
    min_pulse_us: float
    max_pulse_us: float

    @abstractmethod
    def set_pulse_us(self, channel: int, pulse_us: float) -> None:
        pass

    @abstractmethod
    def disable_channel(self, channel: int) -> None:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass
