# SSR-RACK48: 48-channel solid-state relay rack (12 quad modules)

Measurement Computing / Digilent part 6069-410-070, also sold by OMEGA. The model is the mechanical
envelope, for designing enclosures and fasteners.

Sources:
- the Digilent datasheet (January 2026), supplied by the user (`C:\Users\admin\Downloads\SSR-RACK48.pdf`): top-view photo and board layout figure;
- the OMEGA listing: 17 × 4.5 × 1.5 in with relays;
- the user's photo from the header side, showing WRC 1781 quad modules.

**given** = OMEGA listing; **photo** = scaled from the datasheet's top view at about 0.61 mm/px; **estimated** = typical part sizes.

| Item | Value | Source |
|---|---|---|
| PCB | 431.8 × 114.3 mm (17 × 4.5 in), square corners | length **measured** by the user (17 in); width given |
| PCB thickness | 1.6 mm | estimated |
| Overall height with modules | 38.1 mm (1.5 in) | given |
| Mounting holes | 8 × Ø3.5: corners inset 4.8 mm, and at x = L/3 and 2L/3 (in the gaps between module groups), top and bottom edges | photo / estimated |
| Quad SSR modules | 12, in 3 groups of 4. Footprint 30 × 64 mm, centred at y = 48. Pitch 34.5 within a group; groups centred at L/6, L/2, 5L/6. Body 35.3 mm tall, so the LED domes top out at the given 38.1 | photo / estimated |
| Module details | 2 × 2 LED domes, Ø3 × 1.2 with a 1.1 mm round on the top edge, at the header (IC) end; hold-down screw head, Ø5 × 0.5, toward the terminal end | user panel photo / estimated |
| Screw terminals | 3 strips of 24 positions at 5.08 mm (121.9 × 9 × 10 mm) along the y = 0 edge. Each position has a 2.8 mm screw opening on top and a 3.2 mm wire entry in the front face | photo / estimated |
| 50-pin header (P_IO) | 66 × 9 × 9 box header with a 62 × 5 × 7 cavity, centred at (186, 104) | photo / estimated |
| Molex 4-pin power (P20) | 21 × 9 × 11, with a 19 × 7 × 8 shroud, at (353, 105.5) | photo / estimated |
| Buffer ICs | 6 DIP packages, 25 × 7.6 × 4.5, in a row at y = 90 | photo / estimated |
| Port-direction DIP switches | 2 × 4-way, 11 × 10 × 5, near the top corners | photo |

Axes: x along the 17 in edge from the module-48 end, y = 0 at the screw-terminal edge, z up from
the PCB bottom. Everything is fused into one solid.

**Left out:** resistors, LEDs and small parts on the board, the IC sockets, the module pins, the screw-terminal clamps, the silkscreen, and the underside.

**Clearances, checked by hand:**
- Modules (y 16 to 80) clear the terminal strips (y 3 to 12), the ICs (y 86.2 to 93.8) and the header (y 99.5 to 108.5).
- Module groups span 133.5 mm and leave 10.5 mm gaps, where the holes at x = 143.9 and 287.9 sit.
- The terminal strips end 10.9 mm from those holes.

## Expected values

These come from `scripts/board_build.py` `expected()`, which adds up each primitive's exact volume.

- PCB: 431.8 × 114.3 × 1.6 = 78967.58, minus 8 holes of π·1.75²·1.6 (15.39 each), gives 78844.43 (the PCB term in the builder's breakdown)
- Modules: 12 × 30 × 64 × 35.3 = 813312
- LED domes: each Ø3 × 1.2 (8.482) less the round, 1.1² (1 − π/4) · 2π (0.4 + 2.2/(3 (4 − π))) = 2.047, so 6.435 each, 308.9 for all 48. Screw heads 12 × π·2.5²·0.5 = 117.8
- **Total 931280.01 mm³**
- Bounding box: 431.8 × 114.3 × 38.1
