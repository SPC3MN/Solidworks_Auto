# HiFiBerry DAC8x: mechanical model with its components

Used in **flacmn deck pro** (Pi 5 version, decided 2026-11-02 in spcmn
`plans/flacmn-speakers.md`). Reference photos in `references/` (`sources.md`).

Source key: **given** = Raspberry Pi HAT standard and HiFiBerry's listing (55 × 65 × 25 mm,
including headers); **estimated** = judged from the photos against the HAT outline.

| Item | Value | Source |
|---|---|---|
| PCB | 65 × 56.5 × 1.6 mm, r = 3, 4 × Ø2.75 holes on a 58 × 49 mm pattern | given |
| 40-pin header (top) | 2 × 20 at 2.54 mm on the hole line y = 52.5; plastic 2.5 mm, pins 8.5 mm above it | given (position) / estimated (heights) |
| Socket underneath | 50.8 × 5.08 × 8.5 mm, plugs onto the Pi 5 header | estimated |
| 4 × 3.5 mm jacks | bodies 11 × 13 × 6.5 mm at x = 16, 28.5, 41, 53.5, mouths at the front edge; noses Ø6 × 2 mm, bores Ø3.6 | estimated |
| 4 × DAC chips | TSSOP-20, 6.5 × 4.4 × 1.1 mm, stepping from (22, 23) to (53.5, 35) | estimated |
| Small parts | 2 SOT-23, 15 × 0603 + LED, 4 × 0805 | estimated, in `parameters/layout.json` |

Axes as in `rpi_dac_pro`. One fused solid. The overall height came out at 21.1 mm
against the listed 25 mm: the listed figure probably includes packaging tolerance or
a longer pin. Check with calipers if the stack height matters.

## Expected values

- PCB 5863.64 − holes 38.01; header 784.42; components 142.95
- Jack bodies + socket 5911.54; jack noses 144.77
- **Total 12809.30 mm³**, **bounding box 65 × 58.5 × 21.1 mm**
