# Classroom demonstration

1. From the repository root run `.venv/bin/python run.py --mode keyboard`. Press Space, then 1 for upright / 2 for flat. Demonstrate successful passage, deliberately choose the wrong angle, then R to restart. Explain that this is explicitly Keyboard Demo Mode.
2. Close the demo. Run `.venv/bin/python run.py --mode iottalk` on the laptop. Keep one receiver process running at a time.
3. Open the HTTPS Smartphone page on the physical phone, allow motion access, leave the tab foreground and keep the screen awake. In the course project select that exact Smartphone instance and `TiltShift-3D` as output.
4. Show real registration, LIVE status, sample frequency and sample age. Explain the difference between device registration and sensor reception.
5. Calibrate upright then flat. Demonstrate screen up/down equivalence, portrait/landscape upright, and smooth intermediate angles.
6. Play several walls. Background the phone page to demonstrate DELAYED then stale auto-pause; return to the phone page and press Space after LIVE returns.
7. Show actual project wiring and terminal data. Do not use keyboard screenshots as evidence of phone control.

Before class: charge phone/laptop, test the classroom network, prepare keyboard fallback, and capture actual phone-axis measurements plus successful calibration. The deterministic graphical check `.venv/bin/python run.py --seed 7 --smoke` creates genuine local screenshots and exits automatically. It injects keyboard events and controlled geometry for collision checks; it is not a phone hardware test.
