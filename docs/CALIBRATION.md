# Physical phone calibration

The app measures the screen plane's inclination to gravity, not compass heading or a full 3D attitude. For stationary or slowly moving phones, `abs(a_normal) / sqrt(ax²+ay²+az²)` is near zero upright and near one flat. Screen facing up/down is equivalent; rotating portrait/landscape in the screen plane leaves the ratio unchanged.

The default assumes Z is the screen normal. Verify this with your actual phone: flat up and flat down should have |az| near 9.8 m/s², upright should have az near zero, and total magnitude should remain near 9.8. If another axis is normal, set `TILTSHIFT_NORMAL_AXIS=0` or `1` in `.env`. If payload order differs, change `TILTSHIFT_AXES`. Real upright/flat validation is required before claiming hardware accuracy.

1. Select CALIBRATE PHONE. It explicitly switches to IoTtalk and starts the real receiver.
2. Hold upright comfortably, click COLLECT POSE, and hold steady.
3. Hold flat with the screen up or down, click COLLECT POSE again.
4. The wizard saves only after both references pass validation. Play then uses the saved references.

Each collection starts with fresh local receive timestamps and needs at least 8 samples spanning ≥1.4 s. It collects for ≥2.2 seconds, extending up to 4.5 seconds for slow feeds. Last sample age must be ≤.65 s; oldest sample age ≤6 s. Alignment standard deviation must be ≤.065. Gravity magnitude must be 5–15 m/s² with standard deviation ≤1.2, and flat minus upright must be ≥.35. Unstable, corrupted, wrong-unit and insufficiently separated captures are rejected with retry instructions.

Mapping: `angle = 90 × (1 - clamp((alignment-upright)/(flat-upright),0,1))`. The gravity-alignment filter uses time constant .22 s; rendered angle uses .14 s, with exponential frame-time-aware response. Classification uses thresholds 25°/65° and a .3 s dwell; collision uses the rendered physical angle instead of this label.

Profiles in `.local/calibration.json` are keyed by server, receiver ID, phone profile name, normal axis and payload mapping. Set a different `TILTSHIFT_PROFILE` when changing phones; recalibrate after changing phone or sensor convention. These are user-controlled profile identifiers, not automatic hardware detection. Keyboard Demo bypasses sensor calibration explicitly. It never synthesizes phone measurements.
