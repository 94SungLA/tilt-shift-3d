# IoTtalk setup / 課程專案接線

Project: `01257001-宋辰星-tilt-shift-3d-iottalk`.
Server: <https://class.iottalk.tw>. GUI: <https://classgui.iottalk.tw/connection>.
Use the project password privately in the course GUI; never place it in source, .env.example or screenshots.

## Current configuration

This project has been configured through the actual course GUI with:

- Smartphone model, exact feature `Acceleration`, three fields x1/x2/x3.
- Smartphone instance `92.SmartPhone`, as identified by the user.
- Dummy_Device model, output feature `Dummy_Control` only; receiver name `TiltShift-3D`.
- Join 1, all three input types explicitly **sample**, input function `tiltshift_01257001_xyz`, output function `tiltshift_01257001_forward`.

**Do not leave the three input types at `variant`.** Live testing with variant produced near-zero differences, unsuitable for measuring gravity. The application deliberately rejects zero/implausible values and requires stable gravity magnitude for calibration.

Real screenshots are in `docs/screenshots/iottalk-project.png` and `iottalk-join.png`. These are configuration evidence, not evidence that a calibrated phone-controlled game has been played.

## Reproduce the configuration

1. Open <https://class.iottalk.tw> and choose Project; open the named project, entering its password privately if requested.
2. On your physical phone open <https://class.iottalk.tw/da/Smartphone/>. Choose a recognizable device name, allow motion/orientation when prompted (iOS: tap Grant), keep the page foreground and the phone awake. Check that x/y/z change. Reopening can create a new identity, so reselect the exact device instance if needed.
3. Run the laptop receiver from the repository root:

   ```sh
   .venv/bin/python run.py --mode iottalk
   ```

   It launches the original `iottalk-reference/DAI.py tiltshift_sa`, with the project SA on PYTHONPATH. It registers Dummy_Device with **no input features**, only Dummy_Control. Registration success must come from the actual server. Device identity persists in ignored `.local/device.json`. Keep this process running while selecting the GUI device.
4. If constructing from scratch, choose Model → Smartphone, enable only Acceleration, Save. Choose Model → Dummy_Device, enable only **output** Dummy_Control, Save. Do not enable Dummy_Sensor.
5. Click the Smartphone title and select your exact phone, not someone else's device. Click the Dummy_Device title and select `TiltShift-3D` (or the exact configured device name).
6. Click Acceleration, then Dummy_Control to create a Join connection. Click the small Join circle to open its settings.
7. Set each x1/x2/x3 Type to **sample**. In the Acceleration Function selector choose add new function. Give it a unique project-specific name (`tiltshift_01257001_xyz` is already created here), and enter:

   ```python
   def run(*args):
       return [float(args[0]), float(args[1]), float(args[2])]
   ```

   Save the function, close Function Management, select the saved function on Acceleration.
8. On Dummy_Control's output Function choose add new function. Name it `tiltshift_01257001_forward` and use:

   ```python
   def run(*args):
       return args[0]
   ```

   Save, close Function Management, select it as the output function, and click the connection's Save button. These functions preserve continuous XYZ; do not convert to upright/flat labels on the server.
   Ensure the top-bar **Flush** indicator is green. During this session, restoring it from red to green resumed delivery after rebinding. Simulation must remain OFF for real phone validation.

9. Confirm actual Python data with a separate diagnostic run **after closing the game**:

   ```sh
   .venv/bin/python run.py --diagnose 30
   ```

   It prints only real `REAL RECEIVER xyz=... source=... quality=...` samples, or zero samples if none arrive. The parser accepts `[ax,ay,az]` and a single ODF list wrapper `[[ax,ay,az]]`; numeric strings, malformed and nonfinite values are rejected. It timestamps receipt locally and retains the source timestamp from official DAN. Frequency is measured, not assumed. Do not run diagnostic and game concurrently with the same ID.
10. Close the diagnostic, launch IoTtalk mode, choose Calibrate Phone. Collect upright, then flat. After successful validation, select Play. Changing phone requires changing TILTSHIFT_PROFILE or recalibrating.

## Configurable settings

Copy `.env.example` to `.env` if settings need adjustment. The root launcher loads it without overriding existing environment variables. Configure IOTTALK_SERVER, IOTTALK_MODEL, IOTTALK_ODF, IOTTALK_DEVICE_NAME, optional IOTTALK_DEVICE_ID, TILTSHIFT_NORMAL_AXIS (default Z=2), TILTSHIFT_AXES (default 0,1,2), and TILTSHIFT_PROFILE. An alternate feature must exist on your server; configuration does not create server schemas. `TILTSHIFT_ROOT` can identify the source checkout when using an installed CLI from a different working directory. No project password is required by the device registration API.

## Source and verification boundaries

The live server's public [Smartphone ida.js](https://class.iottalk.tw/da/Smartphone/js/ida.js) was inspected: `Acceleration()` returns x/y/z in that order and the motion callback reads `accelerationIncludingGravity`, rounded to 0.1. This establishes the implemented feed convention. Z as screen normal still needs validation with the user's own upright and flat recordings. The official course site [Smartphone page](https://class.iottalk.tw/da/Smartphone/) exposes x/y/z labels.

Verified here: actual official DAI registration, actual project configuration and receipt of phone-originated data. The real 92.SmartPhone recording also verified both poses: upright approximately `(-0.2,-9.8,0.6)` and flat approximately `(-0.2,-0.2,-9.7)`. Across 313 samples, Z alignment ranged from 0.0404 to 0.9997, with median receive frequency 2.79 Hz. A cropped real recording is replayed in pytest. Completed in-game calibration and real phone-controlled passage remain separate hardware checks. A silent sensor stream produces WAITING or STALE, never simulated phone readings.

## Troubleshooting

- Registered but WAITING: select the live receiver and phone instances; keep phone page foreground; inspect Join functions and all three sample types.
- Near-zero/rapidly changing values at rest: ensure types are sample rather than variant. Check the phone page's raw readings and use acceleration including gravity.
- Calibration rejects units: the current validation expects m/s² around 9.8. Do not silently reinterpret g units or arbitrary normalized data.
- Wrong pose: confirm actual normal axis and change configuration, then recalibrate.
- Device disappears after closing app: restart the receiver and reselect its instance if the GUI has detached it.
- Duplicate device conflicts: close other game/diagnostic processes using the same identity.
- Browser permission failure: use HTTPS, tap Grant, allow motion in device/browser settings, reload the phone page and reselect the new registration.
