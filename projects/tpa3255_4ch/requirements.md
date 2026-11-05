# 4-channel TPA3255 class-D amplifier board: electronics envelope

For the deck pro build (Pi 5 + HiFiBerry DAC8x + 4-channel TPA3255). This is
the board named in `flacmn-speakers.md` (Elecbee), photographed on the alexnld
listing; see `references/sources.md`.

**Board size is an assumption.** Listings give either 108 × 94 or 188 × 130 mm.
The photos' proportions (about 1.15 : 1) fit 108 × 94, so that is used here.
Check it against the real board before designing a housing.

| Item | Value | Source |
|---|---|---|
| PCB | 108 × 94 × 1.6, square corners | assumed (see above) |
| Mounting holes | 4 × Ø3.2, 4 mm in from each edge | estimated |
| Heatsink | 88 × 28 × 22 mm bar on the two TPA3255 chips, 5 fins (4 grooves 2 × 7 mm along its length) | estimated |
| TPA3255 ×2 | 14 × 6.1 × 1.2 under the heatsink | estimated (HTSSOP-44 pad-up) |
| Per channel ×4 | 2 output inductors 9.5 × 9.5 × 8; 2 film caps 7.2 × 5 × 9.5; 5.08 mm screw terminal 10.2 × 8 × 10 at the far edge | estimated |
| Power | 4 × Ø8 × 12 bulk caps, 1 screw terminal | estimated |
| Inputs | 4 × XH-3 + 1 × XH-2 (mute) on the front edge | estimated |
| Per input channel | SOIC-8 op-amp, SOT-23, 4 × 0603, 3 × 0603, 1 × 0805, 2 × Ø5 × 5.5 electrolytics | estimated |
| Supply | XL7005 buck inductor 5.8 × 5.2 × 4.5, LM7812 TO-252, 3 × Ø6.3 × 7.7 caps | estimated |

All positions: `design/gen_layout.py` (regenerates `parameters/layout.json`).
Axes: x along the 108 mm edge, y = 0 at the input edge, z up from the PCB bottom.

## Expected values (from `scripts/board_build.py: expected()`)

PCB 16243.20 − holes 51.47; packages with detail 918.42; blocks 67233.28;
cylinders 3996.77; fin grooves −4928.00. **Total 83412.191 mm³**, bounding box **108 × 94 × 24.8**.
