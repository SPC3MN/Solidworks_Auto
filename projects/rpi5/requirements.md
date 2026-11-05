# Raspberry Pi 5: mechanical envelope model

From the user's two photos: a top view (positions) and an angled view (heights).
The photos were only available in the chat, not as files, so positions were
read directly off the top view (about 6.5 px/mm, fitted to the four mounting
holes) instead of from enlarged crops. The model is for case and fit design.

Source key: **given** = Raspberry Pi 4/5 mechanical drawing (board outline and
holes); **photo** = from the top view (±0.7 mm); **estimated** = heights judged
from the angled photo, or typical part sizes.

| Item | Value | Source |
|---|---|---|
| PCB | 85 × 56 × 1.6 mm, r = 3 | given |
| Mounting holes | 4 × Ø2.7 at (3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5) | given |
| J8 GPIO | 2 × 20 at 2.54 mm pitch, centred (32.5, 52.5); plastic 2.5 mm, pins 6 mm above it | given / estimated heights |
| PoE header | 2 × 2 centred (61.3, 9.3), same heights | photo / estimated |
| USB 2 and USB 3 stacks | 18.4 × 13.8 × 16 mm each, overhanging the right edge by 3.6 mm | photo / estimated height |
| Ethernet RJ45 | 22.2 × 16.2 × 13.5 mm, same overhang | photo / estimated height |
| 2 × micro-HDMI, USB-C | 6.5 × 7.5 × 3.2 and 9 × 7.5 × 3.2 mm, 1 mm past the bottom edge | photo / estimated |
| Power button | 3.5 × 3 × 3 mm, 1 mm past the left edge | photo / estimated |
| Chips | BCM2712 with metal lid (2.4 mm), RAM, RP1, wireless shield can, PMIC, Ethernet PHY (rotated 45°), USB hub IC | photo / estimated heights |
| Other | 6 power inductors, 3 SOT-23, 2 LEDs, the PCIe, CAM/DISP 0/1, fan, UART and battery connectors | photo / estimated |

Full list: `parameters/layout.json`. Axes: x along the 85 mm edge (from the
power/USB-C side), y = 0 at the HDMI edge, z up from the PCB bottom. Everything
is fused into one solid.

**Left out:** the individual resistors and capacitors (only 3 to 6 px wide in
the photo, so their positions can't be read), the microSD slot and other
underside parts (not visible), and the silkscreen.

## Expected values (worked out by hand; component sum from `scripts/layout_check.py`)

- PCB: (85·56 − (4−π)·3²)·1.6 − 4·π·1.35²·1.6 = 7603.64 − 36.64 = 7567.00
- J8: 645.16 + 98.30 = 743.46. PoE: 5.08²·2.5 = 64.52 + 4·0.64²·6 = 9.83 → 74.35
- Components (31, none touching, 0.15 mm gap checked): 15582.17
- **Total ≈ 23966.98 mm³**
- **Bounding box**: x −1.0 … 88.6 = 89.6, y −1.0 … 56 = 57.0, z 1.6 + 16 = 17.6
