<!-- projects/encoder_pec11r_15 with the shaft cut 3 mm (flacmn deck round 14: 10 mm caps, shaft tip at the cap face). -->
﻿# Bourns PEC11R-4215F-S0024 (15 mm shaft) rotary encoder: mechanical envelope

For the flacmn / radiomn control knobs. Electronic component only (no knob or
housing). Sources: `references/sources.md`. The LCSC photo has a 1 mm grid,
which gives the rough scale.

| Item | Value | Source |
|---|---|---|
| Body | 12.5 x 13.4 x 6.6 mm | estimated from photos (grid where shown) |
| Bushing | Ø7 × 7 mm, threaded, modelled plain | estimated |
| Shaft | Ø6, cut to 12 mm above the body top, D-flat 1.5 mm deep over the top 5 mm | 15 mm F-type cut 3 mm (the flat stays above the 7 mm bushing) |
| Pins | 3 encoder pins at 2.5 mm pitch on one side, 2 switch pins on the other, 0.8 × 0.3 | estimated |
| Mounting tabs | 2, on the sides | estimated |

Axes: body centred on the origin, z along the shaft, z = 0 at the body bottom.
Thread, detents and the nut and washer are left out.

## Expected values (`scripts/encoder_build.py: expected()`)

Body, bushing, shaft, pins and tabs are plain prisms and cylinders. The D-flat
removes the circular segment r²·acos(d/r) − d·√(r² − d²) over 5 mm.
**Total 1503.925 mm³** (the 15 mm model's 1577.692 less 3 mm of Ø6 shaft, π·3²·3 = 84.823, plus 2 mm of flat no longer cut, 2 × 5.528 = 11.055), bounding box **12.5 × 13.4 × 23.1**.
