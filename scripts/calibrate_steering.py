"""Interactively adjust exactly one steering servo within configured bounds."""

from __future__ import annotations

import argparse

from car.hardware.steering import SteeringServo
from ._common import add_mode_args, load_for_args, make_backend


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("servo", choices=("left", "right"))
    parser.add_argument("--step-us", type=int, default=5)
    add_mode_args(parser)
    args = parser.parse_args()
    config = load_for_args(args)
    cfg = config.steering[args.servo]
    if args.step_us <= 0:
        parser.error("--step-us must be positive")
    backend = make_backend(config, args.real_hardware)
    servo = SteeringServo(backend, cfg)
    pulse = float(cfg.center_us + cfg.trim_us)
    print(f"Operating ONLY {args.servo} steering on channel {cfg.channel}.")
    print("Commands: + / - adjust, c center, p print, q safe center and quit")
    try:
        backend.set_pulse_us(cfg.channel, pulse)
        while True:
            command = input(f"{pulse:.0f} us > ").strip().lower()
            if command == "q":
                break
            if command == "c":
                pulse = float(cfg.center_us + cfg.trim_us)
            elif command == "+":
                pulse += args.step_us
            elif command == "-":
                pulse -= args.step_us
            elif command == "p":
                print(f"Copy candidate value: {pulse:.0f}")
                continue
            else:
                print("Use +, -, c, p, or q")
                continue
            pulse = max(cfg.min_us + cfg.trim_us, min(cfg.max_us + cfg.trim_us, pulse))
            backend.set_pulse_us(cfg.channel, pulse)
        return 0
    finally:
        try:
            servo.center()
        finally:
            backend.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
