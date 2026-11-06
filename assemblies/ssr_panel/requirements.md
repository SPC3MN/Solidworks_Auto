# SSR panel assembly

The electronics on the black acrylic panel in the user's two photos, without the wiring and the
ribbon cable, which were left out at the user's request. `gen.py` generates the part projects and
`assembly.json`; `scripts/assembly.py` builds and checks the assembly.

**Scale:** the SSR-RACK48 is 431.8 mm long (measured by the user) and spans 1230 px in the
straight-on photo, so about 0.351 mm/px. Everything except the rack is **estimated** from that.

| Item | Part | Placement (panel x right, y up, z out) |
|---|---|---|
| Acrylic panel, 340 x 600 x 6.35 | `acrylic_panel` | origin at the bottom-left corner |
| SSR-RACK48 | `ssr_rack48` | turned 90° (length vertical, terminals facing right); centre (170, 292): centred across the panel width (user), on 8 standoffs |
| Standoffs, M2.5 x 11 | `standoff_m25` x 8 | on the rack's hole pattern; matching Ø3 holes in the panel |
| TS35 DIN rail, 469 long | `din_rail_ts35` | centre line x = 36, from y = 79 |
| Screw terminals, 8.2 pitch | `din_terminal` x 48 | 3 groups of 16 (given by the user), tops at y = 530, 375, 220 |
| Power supplies, LRS-150 size (159 x 97 x 30), all three the same (user) | `psu_lrs150` x 3 | on edge at x = 311, y 391 to 550, 211 to 370 and 31 to 190 |

**Checks:**
- 62 components, all present.
- Bounding box 340 x 600 x 103.35. That is the panel plus the supplies: 6.35 + 97.
- No interference. Parts only touch at their mounting faces.

Every part passes its own 9-check pipeline; the rack passes 10.

**Left out:** wiring, the ribbon cable, end stops and labels on the terminal groups, the
supplies' mounting brackets, and the panel's fixing to the frame.
