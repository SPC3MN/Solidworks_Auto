# Raspberry Pi Zero 2 W: mechanical model with its components

Used in **flacmn deck** and **radiomn** (spcmn plans, `flacmn-pi/docs/hardware.md`).
Reference photos are in `references/` (`sources.md` lists where each came from).

Source key: **given** = Raspberry Pi's published mechanical drawing and product
brief; **estimated** = judged from the photos against the given board size.

| Item | Value | Source |
|---|---|---|
| PCB | 65 × 30 mm, corner radius 3 mm | given |
| PCB thickness | 1.0 mm | estimated (confirm with calipers) |
| Mounting holes | 4 × Ø2.75 mm, 3.5 mm in from each edge (58 × 23 mm pattern) | given |
| GPIO | 2 × 20 unpopulated plated holes, Ø1.0, 2.54 mm pitch, centred at (32.5, 26.5) | given (hole size estimated) |
| Mini-HDMI | centre x = 12.4, 11.2 × 7.5 × 3.2 mm, 0.5 mm past the edge | given (x) / estimated (size) |
| Micro-USB (USB, PWR IN) | centres x = 41.4 and 54.0, 8 × 5.5 × 2.9 mm, 0.5 mm past the edge | given (x) / estimated (size) |
| microSD socket | 12 × 11.5 × 1.4 mm at the left end | estimated |
| Camera (CSI) connector | 4.6 × 17 × 1.6 mm at the right end | estimated |
| RP3A0 SiP | 12.5 × 12.5 × 1.2 mm at (29, 13) | estimated |
| Wi-Fi shield can | 10 × 10 × 1.3 mm at (44, 18.5) | estimated |
| Small parts | PMIC (QFN 3 × 3), 3 inductors, crystal, SOT-23, 9 × 0402 | estimated, in `parameters/layout.json` |

Axes: x along the 65 mm edge, y = 0 at the connector edge, z up from the PCB
bottom. One fused solid. The 40-pin header is left out: the Zero 2 W is sold
without one, and deck builders solder their own.

Left out: underside parts and test pads, silkscreen, colours.

## Expected values

Sums of the layout's primitives (`scripts/board_build.py expected()`, independent of SolidWorks):

- PCB 1942.27 − mounting holes 23.76 − GPIO holes 31.42
- Components 1076.89 (package detail from `scripts/details.py`: leads, end caps, connector openings)
- **Total 2963.99 mm³**
- **Bounding box 65 × 30.5 × 4.2 mm** (connectors overhang 0.5 mm; the HDMI socket is the tallest part)

## Port interior (added 2026-11-06)

The mini-HDMI has a centre tongue, 4.2 × 0.6 (**estimated**), recessed 0.5 mm. Volume change: +4.2·0.6·6.5 = +16.38 mm³, so the expected volume is now 2963.99 + 16.38 = **2980.37 mm³**.
