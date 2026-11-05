# Bourns PEC11R-4220K-S0024 rotary encoder: mechanical envelope

For the flacmn / radiomn control knobs. Electronic component only (no knob or
housing). Sources: `references/sources.md`. The LCSC photo has a 1 mm grid,
which gives the rough scale.

| Item | Value | Source |
|---|---|---|
| Body | 12.5 x 13.4 x 6.6 mm | estimated from photos (grid where shown) |
| Bushing | Ø7 × 7 mm, threaded, modelled plain | estimated |
| Shaft | Ø6, 20 mm above the body top, D-flat 1.5 mm deep over the top 10 mm | estimated (common 20 mm F-type) |
| Pins | 3 encoder pins at 2.5 mm pitch on one side, 2 switch pins on the other, 0.8 × 0.3 | estimated |
| Mounting tabs | 2, on the sides | estimated |

Axes: body centred on the origin, z along the shaft, z = 0 at the body bottom.
Thread, detents and the nut and washer are left out.

## Expected values (`scripts/encoder_build.py: expected()`)

Body, bushing, shaft, pins and tabs are plain prisms and cylinders. The D-flat
removes the circular segment r²·acos(d/r) − d·√(r² − d²) over 10 mm.
**Total 1702.481 mm³**, bounding box **12.5 × 13.4 × 31.1**.
