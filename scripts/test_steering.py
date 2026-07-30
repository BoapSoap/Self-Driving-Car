"""Test center and small motions for one servo or both; dry-run by default."""

from __future__ import annotations

import argparse
import time

from car.hardware.steering import SteeringServo
from ._common import add_mode_args, load_for_args, make_backend


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("servo", choices=("left", "right", "both"))
    parser.add_argument("--fraction", type=float, default=0.1, help="small normalized movement")
    parser.add_argument("--pause", type=float, default=0.75)
    add_mode_args(parser)
    args = parser.parse_args()
    if not 0 < args.fraction <= 0.25:
        parser.error("--fraction must be in (0, 0.25]")
    config = load_for_args(args)
    names = list(config.steering) if args.servo == "both" else [args.servo]
    if args.real_hardware:
        uncalibrated = [name for name in names if not config.steering[name].calibrated]
        if uncalibrated:
            raise SystemExit(
                "real steering test requires calibrated=true for: " + ", ".join(uncalibrated)
            )
    backend = make_backend(config, args.real_hardware)
    servos = [SteeringServo(backend, config.steering[name]) for name in names]
    print(f"Operating ONLY steering servo(s): {', '.join(names)}")
    try:
        for label, command in (("center", 0.0), ("small left", -args.fraction),
                               ("center", 0.0), ("small right", args.fraction),
                               ("center", 0.0)):
            print(label)
            for servo in servos:
                servo.set(command)
            time.sleep(args.pause)
        return 0
    finally:
        try:
            for servo in servos:
                servo.center()
        finally:
            backend.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
