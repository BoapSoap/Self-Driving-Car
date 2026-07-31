from __future__ import annotations

import argparse
import signal
from contextlib import contextmanager
from typing import Iterator

from car.config import CarConfig, load_config
from car.hardware.dry_run_backend import DryRunBackend
from car.hardware.pca9685_backend import PCA9685Backend
from car.hardware.pwm_backend import PWMBackend

MOTOR_ACK = "WHEELS_OFF_GROUND"
OUTPUT_ACK = "I_UNDERSTAND_OUTPUT_WILL_MOVE_HARDWARE"


def add_mode_args(parser: argparse.ArgumentParser, *, motor: bool = False) -> None:
    parser.add_argument("--config", help="JSON hardware configuration file")
    parser.add_argument(
        "--real-hardware", action="store_true", help="perform PCA9685 I/O (default: dry-run)"
    )
    parser.add_argument(
        "--acknowledge",
        help=f"required exact acknowledgement: {MOTOR_ACK if motor else OUTPUT_ACK}",
    )


def load_for_args(
    args: argparse.Namespace, *, motor: bool = False, validate_all_hardware: bool = False
) -> CarConfig:
    if args.real_hardware and not args.config:
        raise SystemExit("--real-hardware requires --config; simulation values are forbidden")
    config = load_config(args.config)
    if args.real_hardware:
        expected = MOTOR_ACK if motor else OUTPUT_ACK
        if args.acknowledge != expected:
            raise SystemExit(f"--real-hardware requires --acknowledge {expected}")
        if validate_all_hardware:
            config.validate(for_real_motor_test=True)
    return config


def make_backend(config: CarConfig, real_hardware: bool, *, echo: bool = True) -> PWMBackend:
    c = config.pca9685
    if real_hardware:
        return PCA9685Backend(
            address=c.address,
            frequency_hz=c.frequency_hz,
            min_pulse_us=c.min_pulse_us,
            max_pulse_us=c.max_pulse_us,
        )
    print("DRY-RUN: no hardware I/O will occur.")
    for note in config.notes:
        print(f"CONFIG NOTE: {note}")
    return DryRunBackend(c.min_pulse_us, c.max_pulse_us, echo=echo)


@contextmanager
def stop_signals(callback) -> Iterator[None]:
    previous = {}

    def handler(signum, _frame):
        callback()
        raise KeyboardInterrupt(f"received signal {signum}")

    for sig in (signal.SIGINT, signal.SIGTERM):
        previous[sig] = signal.signal(sig, handler)
    try:
        yield
    finally:
        for sig, old in previous.items():
            signal.signal(sig, old)
