"""Check I2C and PCA9685 visibility without moving any actuator."""

from __future__ import annotations

import argparse

from car.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="JSON config (default address is 0x40)")
    args = parser.parse_args()
    config = load_config(args.config)
    address = config.pca9685.address
    print("No actuator output will be changed.")
    print("Enable I2C with: sudo raspi-config -> Interface Options -> I2C -> Enable")
    try:
        import board

        i2c = board.I2C()
        while not i2c.try_lock():
            pass
        try:
            found = i2c.scan()
        finally:
            i2c.unlock()
        print("Detected I2C addresses:", " ".join(f"0x{x:02X}" for x in found) or "(none)")
        if address not in found:
            print(f"ERROR: configured PCA9685 address 0x{address:02X} was not detected.")
            return 1
        print(f"PASS: device detected at configured address 0x{address:02X}.")
        print("This confirms bus visibility only; it does not verify actuator wiring.")
        return 0
    except Exception as exc:
        print(f"ERROR: I2C is unavailable: {exc}")
        print("Check raspi-config, /dev/i2c-*, wiring, permissions, and Blinka installation.")
        return 2
    finally:
        if "i2c" in locals() and hasattr(i2c, "deinit"):
            i2c.deinit()


if __name__ == "__main__":
    raise SystemExit(main())
