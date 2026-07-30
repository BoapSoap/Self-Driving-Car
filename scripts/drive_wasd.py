"""Terminal WASD controller with ramps, watchdog, e-stop, and safe cleanup."""

from __future__ import annotations

import argparse
import time

from car.control.keyboard import KeyState, TerminalKeyboard
from car.control.slew_limiter import SteeringLimiter, ThrottleLimiter
from car.control.vehicle import Vehicle
from car.control.watchdog import CommandWatchdog
from car.logging.command_logger import CommandLogger
from ._common import MOTOR_ACK, add_mode_args, load_for_args, make_backend, stop_signals


class DemoInput:
    """Finite deterministic input used to verify dry-run without a TTY."""

    def __init__(self, duration_s: float):
        self.started: float | None = None
        self.duration_s = duration_s

    def __enter__(self):
        return self

    def poll(self) -> KeyState:
        now = time.monotonic()
        if self.started is None:
            self.started = now
        elapsed = now - self.started
        if elapsed >= self.duration_s:
            return KeyState(quit=True, had_input=True)
        return KeyState(w=elapsed < self.duration_s / 2, had_input=True)

    def __exit__(self, *_):
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", help="optional JSONL command log")
    parser.add_argument(
        "--demo-seconds", type=float, help="dry-run a finite noninteractive W/stop demo"
    )
    add_mode_args(parser, motor=True)
    args = parser.parse_args()
    if args.demo_seconds is not None and args.demo_seconds <= 0:
        parser.error("--demo-seconds must be positive")
    if args.real_hardware and args.demo_seconds is not None:
        parser.error("--demo-seconds is dry-run only")
    config = load_for_args(args, motor=True, validate_all_hardware=args.real_hardware)
    backend = make_backend(config, args.real_hardware, echo=False)
    throttle_limiter = ThrottleLimiter(
        config.dynamics.throttle_accel_per_s, config.dynamics.throttle_decel_per_s
    )
    steering_limiter = SteeringLimiter(
        config.dynamics.steering_out_per_s, config.dynamics.steering_recenter_per_s
    )
    watchdog = CommandWatchdog(config.watchdog_timeout_s)
    period = 1.0 / config.dynamics.control_hz
    input_context = (
        DemoInput(args.demo_seconds)
        if args.demo_seconds is not None
        else TerminalKeyboard(config.dynamics.key_expiry_s)
    )

    print("\n" + "!" * 72)
    print("WARNING: LIFT ALL WHEELS OFF THE GROUND BEFORE ARMING.")
    print("W forward | S decelerate | A/D steer | SPACE emergency stop | Q quit")
    print("Reverse is disabled. SSH key release is inferred from press expiration.")
    print("!" * 72)
    if not args.real_hardware:
        print(f"DRY-RUN demo. Real activation requires --acknowledge {MOTOR_ACK}")

    vehicle = Vehicle(backend, config)
    logger = CommandLogger(args.log)
    last = time.monotonic()
    last_display = 0.0
    try:
        with stop_signals(vehicle.emergency_stop), input_context as inputs:
            vehicle.arm()
            last = time.monotonic()
            while True:
                loop_started = time.monotonic()
                elapsed = loop_started - last
                last = loop_started
                keys = inputs.poll()
                if keys.had_input:
                    watchdog.refresh()
                if keys.emergency_stop:
                    vehicle.emergency_stop()
                    print("\nEMERGENCY STOP: configured safe ESC outputs commanded.")
                    break
                if keys.quit:
                    break

                watchdog_active = watchdog.expired
                target_throttle = 1.0 if keys.w and not keys.s else 0.0
                if keys.s or watchdog_active:
                    target_throttle = 0.0
                target_steering = 0.0 if keys.a == keys.d else (-1.0 if keys.a else 1.0)

                if watchdog_active:
                    throttle_limiter.stop()
                    vehicle.set_throttle(0.0)
                    applied_throttle = 0.0
                else:
                    applied_throttle = throttle_limiter.update(target_throttle, elapsed)
                    vehicle.set_throttle(applied_throttle)
                applied_steering = steering_limiter.update(target_steering, elapsed)
                vehicle.set_steering(applied_steering)
                snap = vehicle.snapshot()
                logger.log(
                    raw_or_inferred_keys={
                        "w": keys.w, "a": keys.a, "s": keys.s, "d": keys.d,
                        "input_event": keys.had_input,
                    },
                    target_throttle=target_throttle,
                    applied_throttle=applied_throttle,
                    target_steering=target_steering,
                    applied_steering=applied_steering,
                    drive_state=snap.drive_state,
                    pulse_widths_us=snap.pulses_us,
                    emergency_stop=snap.emergency_stopped,
                    watchdog=watchdog_active,
                    mode="hardware" if args.real_hardware else "dry-run",
                )
                if loop_started - last_display >= 0.1:
                    pulses = " ".join(f"{k}={v:.0f}" for k, v in snap.pulses_us.items())
                    print(
                        f"\rthrottle target/applied {target_throttle:.2f}/{applied_throttle:.2f} "
                        f"steering target/applied {target_steering:+.2f}/{applied_steering:+.2f} "
                        f"state={snap.drive_state} watchdog={watchdog_active} {pulses}",
                        end="", flush=True,
                    )
                    last_display = loop_started
                remaining = period - (time.monotonic() - loop_started)
                if remaining > 0:
                    time.sleep(remaining)
        print("\nSafe stop requested.")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted; commanding safe outputs.")
        vehicle.emergency_stop()
        return 130
    except BaseException:
        vehicle.emergency_stop(fault=True)
        raise
    finally:
        logger.close()
        vehicle.close()


if __name__ == "__main__":
    raise SystemExit(main())
