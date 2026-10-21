# Verification record

Date: 2026-10-22 (Asia/Taipei). Platform: local macOS, Apple Silicon, Python 3.14.3, Panda3D 1.10.16.

## Automated

` .venv/bin/python -m pytest -q ` → **50 passed**.

Coverage includes finite acceleration and gravity alignment, normal-axis configuration, portrait/landscape invariance, screen-up/down equivalence, intermediate angle mapping, exponential smoothing, low-frequency input, calibration stability/separation/units, bounded concurrent buffering, malformed/out-of-order payloads, source timestamps, official custom-SA callback naming, keyboard abstraction, collision dimensions, intermediate angles, full-slab swept crossing, rotation during overlap, once-only scoring, deterministic scheduling, difficulty and game states, atomic local persistence, and replay of real upright/flat samples.

` .venv/bin/python -m compileall -q src scripts run.py ` → passed.

## Real rendering

` .venv/bin/python scripts/smoke.py ` → actual CocoaGraphicsPipe window, rotating solid rod, approaching wall with real opening, screenshot and clean automatic exit.

` .venv/bin/python run.py --mode keyboard --seed 7 --smoke ` → actual full-game window; **GRAPHICAL SMOKE PASS: menu, keyboard rotation, pass + score, collision, restart, pause/resume, settings**. The scripted test injects keyboard events and moves one wall forward for collision verification. It is not a hardware-controlled gameplay recording.

Screenshots: `docs/screenshots/menu.png`, `gameplay.png`, `game-over.png`, `pause.png`, `settings.png`, `smoke.png`.

## Real IoTtalk

Original DAI registered against https://class.iottalk.tw, with the server-confirmed name TiltShift-3D. The actual course project was configured through the user's browser: Smartphone/Acceleration → Join 1 → Dummy_Device/Dummy_Control, bound to user-identified 92.SmartPhone.

The initial default variant mapping produced differences around zero. After selecting sample on all three inputs, configuring full XYZ forwarding and enabling green Flush, real acceleration including gravity reached Python. Simulation remained OFF.

313 real samples were recorded locally. Median measured receive frequency: **2.79 Hz**. Representative upright sample: `(-0.2,-9.8,0.6)` m/s²; representative flat sample: `(-0.2,-0.2,-9.7)` m/s². Across movement and both poses, acceleration magnitude ranged 5.63–10.07 m/s² and absolute Z alignment ranged .0404–.9997. This confirms Z as screen normal for the sampled phone. The cropped fixture in `tests/fixtures/phone_92_recorded.json` contains actual readings and source timestamps, without registration keys/passwords. Replay uses relative test timestamps and is explicitly not a live calibration.

Raw session logs stay in ignored `.local/phone-check.log`; no credentials were saved in documentation. Real configuration screenshots are `iottalk-project.png` and `iottalk-join.png`.

## Remaining / limitations

- Complete the in-game calibration wizard with fresh upright and flat samples, then play a real phone-controlled run.
- Verify screen-up versus screen-down physically and record phone disconnect/resume in gameplay; mathematical equivalence is tested.
- Do not claim the recording measures one-way network latency: only receive frequency, local sample age and source timestamps are available.
- Windows, other phone/browser models, Python 3.12 and Ursina have not been tested here.
- Background music now uses the supplied bgm.mp3 through OpenAL, looping at 30% volume with M mute/unmute. Audio output still depends on the system sound device.
- The official client deregisters on exit; if a restarted receiver is unbound, reselect TiltShift-3D in the GUI and ensure Flush is green.
- Source checkout is required for the preserved reference client and custom SA. Use the documented root launcher.
