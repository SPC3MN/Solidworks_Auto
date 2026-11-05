# Raspberry Pi HQ Camera (CS mount): electronics envelope

For the cammn project. Electronic component only: the tripod bracket and any
housing are left out. Sources: the photos in `references/` (see `sources.md`).

| Item | Value | Source |
|---|---|---|
| PCB | 38 × 38 mm, corner r 1 | given (published size) |
| PCB thickness | 1.0 mm | estimated |
| Mounting holes | 4 × Ø2.7 on a 30 × 30 mm pattern, 4 mm in from each edge | estimated from photos |
| Sensor (IMX477) package | 11 × 11 × 1.0 at the centre, glass 7.9 × 6.1 × 0.3 on top | estimated |
| Mount base ring | OD 34, ID 25.4, 3 mm tall | estimated |
| Back-focus lock ring | knurled, 40 teeth, OD 37 (root 35.8), ID 25.4, 4 mm tall | estimated |
| CS-mount tube | OD 31, ID 25.4 (1"-32 thread, modelled plain), 3 mm tall | estimated / 1" thread is standard |
| FFC connector | 21 × 5.5 × 2.5 mm on the underside, 3.5 mm in from the bottom edge | estimated |

Axes: origin at a board corner, z up from the board bottom, lens axis at
(19, 19). Thread, small back-side parts and the C-CS adapter ring are left out.

## Expected values (arithmetic in `design/model.py: expected()`)

- PCB 1443.14 − holes 22.90; sensor 121; glass 14.46; base ring 1203.64;
  lock ring (toothed polygon − bore) × 4; tube 744.18; FFC 288.75
- **Total = 5922.512 mm³**. Hand check with a mean-radius ring instead of the teeth: ≈ 5928.
- **Bounding box**: 38 × 38 × 13.5 (FFC 2.5 below, tube top 11.0 above the board bottom)
