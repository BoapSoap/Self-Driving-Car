import pytest

from car.control.slew_limiter import SteeringLimiter, ThrottleLimiter


def test_acceleration_and_deceleration_rates():
    limiter = ThrottleLimiter(0.5, 1.25)
    assert limiter.update(1.0, 1.0) == pytest.approx(0.5)
    assert limiter.update(0.0, 0.2) == pytest.approx(0.25)
    assert limiter.update(0.0, 1.0) == 0


def test_steering_out_and_recenter_rates():
    limiter = SteeringLimiter(2.5, 10 / 3)
    assert limiter.update(1.0, 0.2) == pytest.approx(0.5)
    assert limiter.update(0.0, 0.1) == pytest.approx(1 / 6)
    assert limiter.update(0.0, 0.1) == 0
