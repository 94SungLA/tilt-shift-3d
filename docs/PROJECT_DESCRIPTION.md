# TiltShift 3D

TiltShift 3D is a smartphone-controlled endless 3D obstacle survival game built with Python and Panda3D. Players rotate a glowing rod to fit vertical or horizontal openings in approaching walls. Holding the phone upright makes the rod vertical; holding it flat makes the rod horizontal, with smooth intermediate rotation.

The system uses the university IoTtalk platform and the official Dummy Device v1 Python framework. Smartphone Acceleration is forwarded through a project Join Function to Dummy_Control. A project-specific SA callback transfers real accelerometer samples to a thread-safe input buffer. Gravity alignment, two-pose calibration, filtering, freshness checks and safe disconnect pauses support low-frequency sensor updates.

Geometry-aware swept collision detection accounts for rod dimensions, angle, wall depth and frame-to-frame movement. The game includes deterministic obstacle generation, three difficulty phases, scoring, menus, saved best score, calibration profiles and an explicitly labeled offline keyboard demo. Pure logic tests and an optional real-window smoke test separate verified behavior from phone-dependent validation.
