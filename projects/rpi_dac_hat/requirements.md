# Raspberry Pi DAC+ HAT: simplified mechanical model

From a product photo (`references/photo.png`, supplied by the user). The model
is for fit checks and enclosure design, so the solid envelopes matter, not the
electrical detail.

## Dimensions

Source key: **given** = from the Raspberry Pi HAT mechanical standard; **estimated** =
judged from the photo against the board size. The photo has no scale reference
of its own.

| Item | Value | Source |
|---|---|---|
| PCB outline | 65 × 56.5 mm, corner radius 3 mm | given |
| PCB thickness | 1.6 mm | given |
| Mounting holes | 4 × Ø2.75 mm (M2.5 clearance), 3.5 mm in from each edge (58 × 49 mm pattern) | given |
| 40-pin header | 2 × 20, 2.54 mm pitch, centred on the long edge along the hole line (y = 52.5) | given |
| Header plastic | 50.8 × 5.08 × 2.5 mm | given (standard part) |
| Header pins | 0.64 mm square, 6 mm above the plastic | estimated |
| RCA sockets (×2) | housing 10 × 12 × 12 mm on the board; front flange 11 × 1.5 × 12 mm; barrel Ø8, sticking out 9 mm past the board edge; socket bore Ø5 × 9 mm deep; axis 6 mm above the board | estimated |
| RCA positions | centres at x = 34 and x = 46 mm, on the edge opposite the header | estimated |
| 3.5 mm jack | body 7 × 12 × 6 mm at x = 56; nose Ø5 sticking out 2.5 mm; bore Ø3.5; axis 3 mm above the board | estimated |
| DAC chip | 8 × 4.5 × 1.5 at (26, 30) | estimated |
| Small parts | 3 small ICs, 1 SOT-23, 30 × 0603, 7 × 0805, 6 × 0402, a 2 × 4 grid of test pads; layout in `parameters/smd_layout.json` | estimated |

Positions come from a photo-to-board mapping fitted to the four mounting holes
(the photo hole centres are about (285,305), (515,185), (335,85) and (100,190) px).
The two small ICs moved to (46.1, 38.4) and (51.8, 27.0), and the DAC came out at
(25.3, 29.9), which confirms the first estimate. The passives are placed by
cluster, near where the photo shows them; individual positions are not exact.

Axes: x runs along the 65 mm edge and y along the 56.5 mm edge, with y = 0 at the
connector edge. Height is z, with the bottom of the PCB at z = 0. Everything is
fused into one solid.

Left out: the solder pins under the board, silkscreen and colours.

## Expected values, worked out by hand

- PCB: (65·56.5 − (4−π)·3²) · 1.6 − 4·π·1.375²·1.6 = 5863.64 − 38.01 = 5825.63 mm³
- Header plastic 645.16. Pins 40 · 0.64² · 6 = 98.30.
- Each RCA: housing 1440 + flange 198 + barrel π·4²·7.5 = 376.99 (the part
  past the flange), minus a bore π·2.5²·9 = 176.71 (cut through flange and
  barrel) = 1838.28. Two of them: 3676.56.
- Jack: body 504 + nose π·2.5²·2.5 = 49.09 − bore π·1.75²·2.5 = 24.05 → 529.03
- Chips: DAC 54 + U2 16 + U3 9 = 79
- Small parts: U4 3·3·0.9 = 8.1; SOT-23 2.9·1.3·1.1 = 4.147; 30 × 0603 (0.576 each) = 17.28;
  7 × 0805 (1.5) = 10.5; 6 × 0402 (0.175) = 1.05; 8 pads π·0.75²·0.1 = 1.414 → 42.49
- **Total volume ≈ 10896.17 mm³** (10853.68 before the small parts). The small
  parts never touch each other or the other components, so their volumes simply
  add up.
- **Bounding box**: x 65 (board), y 56.5 + 9 = 65.5 (RCA barrels), z 1.6 + 12 = 13.6 (RCA housing).
