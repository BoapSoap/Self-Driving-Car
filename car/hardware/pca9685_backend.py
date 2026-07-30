"""Real PCA9685 backend using maintained Adafruit CircuitPython libraries."""

from __future__ import annotations

from .pwm_backend import PWMBackend, PWMError, microseconds_to_duty_cycle, validate_pulse_us


class PCA9685Backend(PWMBackend):
    def __init__(
        self,
        *,
        address: int = 0x40,
        frequency_hz: float = 50.0,
        min_pulse_us: float = 500,
        max_pulse_us: float = 2500,
    ):
        self.min_pulse_us = min_pulse_us
        self.max_pulse_us = max_pulse_us
        self.frequency_hz = frequency_hz
        self._pca = None
        self._i2c = None
        try:
            import board
            from adafruit_pca9685 import PCA9685

            self._i2c = board.I2C()
            self._pca = PCA9685(self._i2c, address=address)
            self._pca.frequency = frequency_hz
        except Exception as exc:
            self.shutdown()
            raise PWMError(
                f"Could not initialize PCA9685 at 0x{address:02X}. "
                "Check Raspberry Pi I2C, shared ground, wiring, address, and dependencies."
            ) from exc

    def set_pulse_us(self, channel: int, pulse_us: float) -> None:
        if self._pca is None:
            raise PWMError("PCA9685 is not initialized")
        if not 0 <= channel <= 15:
            raise ValueError("channel must be in 0..15")
        validate_pulse_us(pulse_us, self.min_pulse_us, self.max_pulse_us)
        self._pca.channels[channel].duty_cycle = microseconds_to_duty_cycle(
            pulse_us, self.frequency_hz
        )

    def disable_channel(self, channel: int) -> None:
        if self._pca is not None:
            self._pca.channels[channel].duty_cycle = 0

    def shutdown(self) -> None:
        pca, i2c = self._pca, self._i2c
        self._pca = None
        self._i2c = None
        if pca is not None:
            try:
                pca.deinit()
            except Exception:
                pass
        if i2c is not None and hasattr(i2c, "deinit"):
            try:
                i2c.deinit()
            except Exception:
                pass
