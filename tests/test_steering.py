import pytest

from car.config import ServoConfig
from car.hardware.dry_run_backend import DryRunBackend
from car.hardware.steering import SteeringServo


def make_servo(*, inverted=False, trim=0):
    return SteeringServo(
        DryRunBackend(echo=False),
        ServoConfig(0, center_us=1500, min_us=1200, max_us=1900,
                    inverted=inverted, trim_us=trim),
    )


def test_independent_piecewise_interpolation():
    servo = make_servo()
    assert servo.pulse_for(-0.5) == 1350
    assert servo.pulse_for(0) == 1500
    assert servo.pulse_for(0.5) == 1700


def test_mirrored_servo():
    normal = make_servo()
    mirrored = make_servo(inverted=True)
    assert normal.pulse_for(1) == 1900
    assert mirrored.pulse_for(1) == 1200


def test_trim_and_endpoint_clamping():
    servo = make_servo(trim=20)
    assert servo.pulse_for(-99) == 1220
    assert servo.pulse_for(99) == 1920
