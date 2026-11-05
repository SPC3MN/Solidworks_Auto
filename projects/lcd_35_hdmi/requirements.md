# Waveshare 3.5inch HDMI LCD: electronics envelope

The user chose this header-mounted screen (2026-11-05), even though the
flacmn-pi `hardware.md` asks for a USB-powered one that doesn't sit on the pin
header. Sources: `references/sources.md` (Waveshare, Core Electronics, Melopero).

| Item | Value | Source |
|---|---|---|
| PCB | 85.42 × 55.92 × 1.6, r 1 | estimated (Pi B footprint) |
| Mounting holes | 4 × Ø2.75 on the Pi pattern (3.5 / 61.5, 3.5 / 52.5) | Pi standard (matches the photos) |
| LCD module + resistive touch | 80.5 × 54.92 × 4.2 on the PCB, active area 73.44 × 48.96 recessed 0.2 | estimated (3.5" 480 × 320 panel) |
| Panel flex tail | 2 × 30 × 0.4 at the right edge | estimated |
| GPIO socket (underside) | 2 × 13 female, 33.02 × 5.08 × 8.5, 26 square 1 mm pin holes, over the Pi GPIO pins 1–26 | Pi standard position / estimated height |
| HDMI (underside) | full-size, 15 × 11.5 × 5.6 at x = 32, 0.5 mm past the edge, 14 × 4.5 opening | estimated |
| 3.5 mm jack (underside) | body 6 × 12 × 5 at x = 53.5, nose Ø5 × 2.5 with a Ø3.5 bore | estimated |

Axes: x along the 85.42 mm edge, y = 0 at the HDMI edge, z up from the PCB
bottom (underside parts at z < 0). The small ICs and passives on the
underside are left out (not visible in the photos).

## Expected values (`scripts/board_build.py: expected()`)

PCB 7641.33 − holes 38.01; LCD and flex 18592.45; underside parts 2751.80;
jack nose 25.04; cuts −1633.12 (recess 719.13, HDMI opening 693.00, socket holes 221.00).
**Total 27339.477 mm³**, bounding box **85.42 × 58.42 × 14.3**.
