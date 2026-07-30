import pytest

from car.hardware.pwm_backend import microseconds_to_duty_cycle, validate_pulse_us


def test_microseconds_to_duty_cycle_at_50_hz():
    assert microseconds_to_duty_cycle(1500, 50) == round(1500 / 20000 * 65535)


def test_pulse_validation():
    validate_pulse_us(1500, 500, 2500)
    with pytest.raises(ValueError):
        validate_pulse_us(499, 500, 2500)
    with pytest.raises(ValueError):
        microseconds_to_duty_cycle(25000, 50)
