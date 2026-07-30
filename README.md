# Raspberry Pi 5 four-wheel-drive car: safe control foundation

This milestone provides hardware-independent steering and forward-throttle control,
safe diagnostics, a terminal WASD controller, and JSONL command logging. Camera,
game-controller, data-collection, autonomous-driving, and reverse-drive behavior
are intentionally outside this milestone.

> **Safety:** Lift all wheels off the ground for every powered motor test. Aircraft
> ESC behavior varies. The repository's example channels and pulse widths are
> simulation placeholders, not recommendations. Do not set the verification flags
> until the corresponding values have been physically established.

## Electrical assumptions

- Raspberry Pi 5 supplies only 3.3 V PCA9685 logic/I2C.
- Steering servos and ESC/motors have suitable external power.
- Pi, PCA9685, servo supply, and ESC signal grounds are shared.
- Nothing in this software switches or manages power.
- The planned battery is a compatible 3S pack. Confirm every component, connector,
  regulator, current rating, and polarity before connecting it.
- Motor direction is established by motor/ESC wiring; do not use an unverified
  throttle signal as a direction control.

The real backend uses maintained `adafruit-blinka` and
`adafruit-circuitpython-pca9685`, importing `PCA9685` from
`adafruit_pca9685`. Blinka supplies the CircuitPython hardware interfaces on
Raspberry Pi OS. This project intentionally does not use `pigpio`,
`RPi.GPIO` for PCA9685 control, a hand-written register driver, or the deprecated
`Adafruit_Python_PCA9685` package.

## Raspberry Pi OS setup

Enable I2C:

```bash
sudo raspi-config
# Interface Options -> I2C -> Enable, then reboot if requested
```

Create an isolated environment and install dependencies:

```bash
cd ~/Self-Driving-Car
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run hardware-free tests:

```bash
python -m pytest -q
python -m scripts.drive_wasd --demo-seconds 2
```

All actuator scripts are dry-run unless `--real-hardware` is supplied. Omitting
`--config` selects conspicuously labelled simulation values. Real output always
requires a config file and an exact acknowledgement.

## Configuration and calibration gates

Copy the example outside the tracked filename and edit the copy:

```bash
cp config/hardware.example.json hardware.json
```

`config/hardware.example.json` contains intentionally unverified simulation values.
Obtain and enter all of these before a full real-hardware run:

- actual PCA9685 address and desired measured/verified PWM frequency;
- front-left, front-right, rear-left, and rear-right throttle channels;
- left and right steering channels;
- each servo's conservative minimum, physical center, conservative maximum,
  inversion, and trim;
- each ESC's safe, arming, minimum-moving, conservative test-maximum, and full
  calibrated-maximum pulse widths;
- confirmed arming duration and arming procedure compatibility;
- any per-motor setting used by the installed wiring;
- verified shared signal ground and which ESC lead(s) provide signal/ground;
- whether the Skywalker Reverse Brake feature needs a separate signal channel and,
  only after separate physical investigation, its exact signal behavior.

Leave all `calibrated` fields false until that actuator has actually been checked.
`hardware_configuration_verified` means an operator has reviewed the real channel
map, wiring, pulse values, and safe limits; it is not set automatically. Keep
`reverse_physically_verified` false. Reverse remains rejected even if that flag is
changed because reverse command logic is deliberately not implemented yet.

The four ESCs have independent configuration entries. `test_max_us` is the
conservative software ceiling and must not exceed `calibrated_max_us`. The built-in
dynamics correspond to about 2.0 s up, 0.8 s down, 0.4 s steering outward, and
0.3 s recentering. Ramps use monotonic elapsed time rather than loop counts.

## Safest diagnostic order

Keep servo/motor external power disconnected while editing and checking wiring.
Replace the example path below with the reviewed `hardware.json`.

1. Confirm I2C visibility. This script scans the bus and sends no PWM:

   ```bash
   python -m scripts.check_i2c --config hardware.json
   ```

2. With only one selected steering servo mechanically safe to move, test the
   configured center and make 5 µs deliberate adjustments:

   ```bash
   python -m scripts.calibrate_steering left --config hardware.json
   python -m scripts.calibrate_steering left --config hardware.json --real-hardware \
     --acknowledge I_UNDERSTAND_OUTPUT_WILL_MOVE_HARDWARE
   ```

   Start with conservative bounds supplied from the physical setup. Copy the
   observed values back to `hardware.json`, then set only that servo's
   `calibrated` flag true.

3. Test only that servo at center and ±10% of its configured travel:

   ```bash
   python -m scripts.test_steering left --config hardware.json
   python -m scripts.test_steering left --config hardware.json --real-hardware \
     --acknowledge I_UNDERSTAND_OUTPUT_WILL_MOVE_HARDWARE
   ```

   Repeat calibration and the small-motion test for `right`; test `both` only
   after each is individually safe.

4. Disconnect motor power, verify one ESC's signal channel and measured pulse
   configuration, set that ESC's `calibrated` true, and review the entire wired
   channel map before setting `hardware_configuration_verified` true. Lift all
   wheels, mechanically restrain the chassis, clear the area, then reconnect power.
   Run the selected ESC dry first:

   ```bash
   python -m scripts.test_esc front_left --config hardware.json
   python -m scripts.test_esc front_left --config hardware.json --real-hardware \
     --acknowledge WHEELS_OFF_GROUND
   ```

   The real script operates only that ESC, starts and ends at its configured safe
   pulse, performs its configured arm sequence, requests 1% of the conservative
   test range for 0.5 s, and never requests reverse. Repeat one ESC at a time.

5. Only after both servos and all four ESCs are individually calibrated, all
   `calibrated` fields are true, the configuration validates, and the wheels remain
   lifted, test the complete controller:

   ```bash
   python -m scripts.drive_wasd --config hardware.json --demo-seconds 2
   python -m scripts.drive_wasd --config hardware.json --log logs/commands.jsonl
   python -m scripts.drive_wasd --config hardware.json --real-hardware \
     --acknowledge WHEELS_OFF_GROUND --log logs/commands.jsonl
   ```

The generic single-channel tool is available for expert diagnostics but does not
know whether a pulse is safe for the connected device:

```bash
python -m scripts.test_pwm_channel --channel 0 --pulse-us 1500
python -m scripts.test_pwm_channel --channel 0 --pulse-us 1500 \
  --config hardware.json --real-hardware \
  --acknowledge I_UNDERSTAND_OUTPUT_WILL_MOVE_HARDWARE
```

## Runtime safety behavior

Module import never initializes hardware. Backend and vehicle construction are
explicit. Vehicle startup immediately commands every configured ESC safe and
centers the steering servos; it does not arm. ESC states are `DISABLED`, `SAFE`,
`ARMING`, `ARMED`, `FORWARD`, and `FAULT`. Throttle is rejected before successful
arming and negative throttle is always rejected.

Space commands an immediate persistent emergency stop. Q safely exits. SIGINT,
SIGTERM, normal exit, keyboard interruption, and exceptions all flow through safe
output cleanup before PCA9685 deinitialization. A partial initialization or arm
failure commands best-effort safe/fault outputs and never silently falls back to
dry-run.

The input watchdog has a maximum 300 ms timeout. If no valid input event refreshes
it, the throttle limiter is reset and configured safe throttle is sent immediately.
Logging failures are ignored so they cannot block emergency stop or cleanup.

SSH terminals do not reliably report true key-up events. WASD state is inferred
from recently repeated keypresses, expiring after 180 ms by default. This can feel
different across SSH clients and is intentionally isolated behind an input-provider
interface. A future game controller should replace that provider while continuing
to use the same normalized `Vehicle` interface.

## Project layout

```text
car/
  config.py
  hardware/     # backend interface, PCA9685, dry-run, steering, ESC
  control/      # vehicle, slew limiters, watchdog, terminal keyboard
  logging/      # best-effort JSONL command logger
config/
  hardware.example.json
scripts/
  check_i2c.py
  test_pwm_channel.py
  calibrate_steering.py
  test_steering.py
  test_esc.py
  drive_wasd.py
tests/
```

No claim of physical hardware verification is made by this repository or its
software-only tests.
