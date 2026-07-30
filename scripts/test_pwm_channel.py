"""Send one explicit pulse to one channel; dry-run by default."""

from __future__ import annotations

import argparse

from car.hardware.pwm_backend import validate_pulse_us
from ._common import add_mode_args, load_for_args, make_backend


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", type=int, required=True)
    parser.add_argument("--pulse-us", type=float, required=True)
    add_mode_args(parser)
    args = parser.parse_args()
    config = load_for_args(args)
    if not 0 <= args.channel <= 15:
        parser.error("--channel must be in 0..15")
    validate_pulse_us(
        args.pulse_us, config.pca9685.min_pulse_us, config.pca9685.max_pulse_us
    )
    backend = make_backend(config, args.real_hardware)
    try:
        backend.set_pulse_us(args.channel, args.pulse_us)
        print("Output sent. This script does not infer whether that pulse is safe for an actuator.")
        return 0
    finally:
        backend.disable_channel(args.channel)
        backend.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
