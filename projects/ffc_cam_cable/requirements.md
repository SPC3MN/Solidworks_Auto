# Camera ribbon cable: Pi 5 CAM/DISP0 → HQ camera

Used in `assemblies/pi5_hq_camera`. Flat flex cable 0.15 mm thick (**estimated**,
typical FFC). It is drawn 13 mm wide at both ends so the path stays in one plane.
The real Pi 5 cable is narrower at the Pi end (22-pin, 0.5 mm pitch) and 16 mm at
the camera (15-pin), so the width is **estimated**.

Path, in Pi 5 board coordinates (x, z), at y 3.2…16.2 (centred on the connector at y = 9.7):

1. Up from the top of CAM/DISP0 (x 54.6, z 1.6 + 3 = 4.6) to z 22. That clears the RJ45, whose top is at 15.1.
2. Along +x to x 95, past the USB and RJ45 overhang (x ≤ 88.6).
3. Down to z 9.75, the middle of the camera's underside connector (the camera sits on 11 mm standoffs and its connector is 2.5 mm tall).
4. Along +x to x 100.75, the face of the camera connector.

The bends are sharp mitres; a real cable bends with a radius of a few mm.

## Expected values

- Centreline length 17.4 + 40.4 + 12.25 + 5.75 = 75.8 mm. A mitred thick polyline has area length × t.
- Volume = 75.8 · 0.15 · 13 = **147.81 mm³**
- Bounding box: x 54.525 … 100.75 = 46.225, y 13, z 4.6 … 22.075 = 17.475
