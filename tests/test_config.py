import copy

import pytest

from car.config import ConfigurationError, simulation_config


def test_simulation_config_is_valid_but_not_hardware_ready():
    config = simulation_config()
    config.validate()
    with pytest.raises(ConfigurationError):
        config.validate(for_real_motor_test=True)


def test_rejects_overlapping_channels():
    config = simulation_config()
    config.motors["front_left"].channel = config.steering["left"].channel
    with pytest.raises(ConfigurationError, match="overlaps"):
        config.validate()


def test_rejects_bad_servo_relationship():
    config = simulation_config()
    config.steering["left"].center_us = config.steering["left"].max_us + 1
    with pytest.raises(ConfigurationError, match="min_us"):
        config.validate()


def test_rejects_test_limit_above_calibrated_limit():
    config = simulation_config()
    config.motors["front_left"].test_max_us = 2100
    with pytest.raises(ConfigurationError, match="exceeds"):
        config.validate()


def test_verified_reverse_requires_explicit_configuration():
    config = simulation_config()
    config.reverse_physically_verified = True
    with pytest.raises(ConfigurationError, match="verified reverse"):
        config.validate()
