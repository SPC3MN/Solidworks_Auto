# GY-PCM5102 (PCM5102A) I2S DAC board: mechanical model with its components

Used in **flacmn deck** and **radiomn** ("the common purple GY-PCM5102",
`flacmn-pi/docs/hardware.md`). Reference photos in `references/` (`sources.md`).

Source key: **listed** = the board size three sellers agree on; **estimated** =
judged from the photos against that size. These are clone boards, so check one
with calipers before designing tight mounts.

| Item | Value | Source |
|---|---|---|
| PCB | 32 × 17 × 1.6 mm, corner radius 0.5 | listed (thickness, radius estimated) |
| Control pins | 1 × 6 holes Ø1.0 at 2.54 mm on the left end (SCK, BCK, DIN, LCK, GND, VIN) | estimated |
| Config pins | 1 × 9 holes Ø1.0 at 2.54 mm along the far edge | estimated |
| PCM5102A | TSSOP-20, 6.5 × 4.4 × 1.1 mm at (13.5, 8.5) | estimated |
| 3.5 mm jack (PJ-320 type) | body 6 × 12 × 5 mm at x = 26.5, mouth at the front edge; nose Ø5 × 2 mm, bore Ø3.5 | estimated |
| Small parts | 2 SOT-23 regulators, 9 × 0603, 1 × 0805 | estimated |

Axes: x along the 32 mm edge, y = 0 at the jack's edge, z up from the PCB bottom.
The header strips ship loose, so they're left out.

## Expected values

- PCB 870.06 − pin holes 18.85; components 43.27; jack body 360.00 + nose 20.03
- **Total 1274.51 mm³**, **bounding box 32 × 19 × 6.6 mm**
