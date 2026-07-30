"""Arm and minimally test exactly one ESC; reverse is never attempted."""

from __future__ import annotations

import argparse
import time

from car.hardware.esc import ESC
from ._common import MOTOR_ACK, add_mode_args, load_for_args, make_backend


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("motor", choices=("front_left", "front_right", "rear_left", "rear_right"))
    parser.add_argument("--throttle", type=float, default=0.01)
    parser.add_argument("--duration", type=float, default=0.5)
    add_mode_args(parser, motor=True)
    args = parser.parse_args()
    if not 0 < args.throttle <= 0.05:
        parser.error("--throttle must be in (0, 0.05] for this initial test")
    config = load_for_args(args, motor=True)
    cfg = config.motors[args.motor]
    if args.real_hardware:
        if not config.hardware_configuration_verified:
            raise SystemExit("real ESC test requires hardware_configuration_verified=true")
        if not cfg.calibrated:
            raise SystemExit(f"real ESC test requires motors.{args.motor}.calibrated=true")
    backend = make_backend(config, args.real_hardware)
    esc = ESC(backend, cfg)
    print("\n" + "!" * 72)
    print("WARNING: LIFT ALL WHEELS OFF THE GROUND. REMOVE PROPELLERS IF APPLICABLE.")
    print(f"Operating ONLY {args.motor} ESC on PCA9685 channel {cfg.channel}.")
    print("REVERSE WILL NOT BE TESTED.")
    print("!" * 72)
    if not args.real_hardware:
        print(f"Real use additionally requires --acknowledge {MOTOR_ACK}")
    try:
        esc.safe()
        esc.arm(config.arming_duration_s)
        esc.set_throttle(args.throttle)
        time.sleep(args.duration)
        esc.safe()
        print("Test complete; configured safe pulse restored.")
        return 0
    finally:
        try:
            esc.safe()
        finally:
            backend.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
