# Raspberry Pi DAC Pro: mechanical model with all visible components

Source: the user's top-view photo (`references/top_view.png`, 474 × 474 px).
Every small part is positioned from that photo, using a pixel-to-mm mapping
fitted to the four mounting holes (≈ 4.2 px/mm, so positions are good to about
±0.5 mm). Heights can't be seen in a top view, so they are standard package
heights or estimates.

Source key: **given** = Raspberry Pi HAT mechanical standard; **photo** = measured
from the top view with the mapping above; **estimated** = guessed.

| Item | Value | Source |
|---|---|---|
| PCB | 65 × 56.5 × 1.6 mm, r = 3, 4 × Ø2.75 holes on a 58 × 49 pattern | given |
| J1 40-pin header | 2 × 20 at 2.54 mm pitch on the hole line y = 52.5; plastic 2.5 mm, pins 6 mm above it | given / estimated heights |
| P7 balanced-out header | 1 × 6 at 2.54 mm pitch, centred at (2.8, 32.8), along y; same height as J1 | photo / estimated |
| RCA block (2 sockets in one housing) | housing x 12.0–39.6, y 0–14, 13 mm tall; front plate 28.6 × 1.5 × 13 mm; barrels Ø8 at x = 18.36 and 32.98, axis 6.5 mm above the board, sticking out 9 mm; bores Ø5 × 9 mm | photo (outline) / estimated (heights, barrels) |
| 3.5 mm jack P3 | body 8 × 12 × 6 mm at x = 51.8; nose Ø5 × 2.5 mm; bore Ø3.5 | photo / estimated |
| Small parts | 2 QFN, 5 SOT-23, 2 SOD-323, 64 × 0603, 5 × 0805, 15 × 0402; pads P5 (2 × 4), P6 (1 × 5), P10 (2), 3 test points | photo, in `parameters/layout.json` |

Axes as in `rpi_dac_hat`: x along the 65 mm edge, y = 0 at the connector edge,
z up from the PCB bottom. The model is one fused solid.

Left out: the pins on the underside, the silkscreen, colours, and any parts too
small to make out in the photo.

## Expected values (worked out by hand; component sum from `scripts/layout_check.py`)

- PCB 5825.63 (same board as the DAC+ model)
- J1: plastic 50.8·5.08·2.5 = 645.16, pins 40·0.64²·6 = 98.30 → 743.46
- P7: plastic 2.54·15.24·2.5 = 96.77, pins 6·0.64²·6 = 14.75 → 111.52
- RCA block: housing 27.6·14·13 = 5023.20; plate 28.6·1.5·13 = 557.70;
  barrels 2·π·4²·7.5 = 753.98 (the part past the plate); bores −2·π·2.5²·9 = −353.43 → 5981.45
- Jack: 8·12·6 = 576 + nose π·2.5²·2.5 = 49.09 − bore π·1.75²·2.5 = 24.05 → 601.03
- Small parts and pads: 112.30 (114 items, none touching, checked with a 0.15 mm gap)
- **Total ≈ 13375.39 mm³**
- **Bounding box**: x 65, y 56.5 + 9 = 65.5, z 1.6 + 13 = 14.6
