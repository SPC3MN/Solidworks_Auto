# airmn bench prototype: requirements

Source: spcmn design brief `plans/airmn-prototype-brief.md` (spcmn-studio/spcmn, 2026-11-08), a copy of the
Claude Doc "airmn prototype: design brief". Values from the brief are **given**. Values the engineer has to
choose are **chosen** here, and sizes of bought parts not in the brief are **estimated**.

Geometry: `airmn_parts.py` (one function per part, volumes by hand). Values: `gen_projects.py`, which writes
every `projects/airmn_<part>/` project and both assemblies. Axis: z up, z = 0 at the bottom cap's underside, the
unit's axis on the origin.

## Current design (7th pass, 2026-11-08): low fan head, tuned for low noise

The owner asked for a smaller fan head with the motor cup down in the filter core, and for the motor mount to
double as a flow conditioner into the fan, designed for the lowest noise. Changes from the 6th pass below:

- **Motor in the core.** The cup is 100 / 90 × 90, open at the bottom, and the motor goes in from below with its
  shaft up. The 5 mm plate on top is the motor mount: 2 × M3 from above, in counterbores. The rotor sits 1 mm
  over the plate, with 6 mm of shaft in the hub. The clamp screw is now 3 mm above the hub's bottom.
- **Struts are the flow straightener.** There are 11 flat radial struts, 3 × 40, from the cup to the inlet
  opening. They do not turn the air: they take out the swirl and unevenness from the pleats so the rotor takes in
  a smooth flow. Their trailing edges, at the flange top, are 50 mm (about 1.25 blade chords) below the rotor.
- **No outlet vanes.** The outlet vanes from the 6th pass are gone. The leftover swirl costs about 0.1 Pa
  (upflow estimate), and the top grid takes out part of it.
- **Grid 40 mm above the rotor.** The fan head is 179 tall (cup bottom to top) and sits 153 above the frame rim,
  down from 285. The unit is 621 tall plus 5 mm feet, down from 758.

Noise reasoning:
- **Wake spacing.** No surface sits in a rotor wake within one chord, and the struts' wakes have 1.25 chords to
  mix out before the rotor.
- **Tyler–Sofrin counts.** The blade-passing frequency is about 31 Hz (265 rpm × 7). Only plane waves travel in
  the 404 duct below about 500 Hz, so the interaction tone only escapes where 7n = 11k. The first such tone is the
  11th harmonic, which is very weak. Five struts would put one at the 5th harmonic.
- **Gearbox whine.** This is probably the loudest source. Having the motor inside the pleat pack puts the media
  round it as an absorber.

Not done yet: swept struts (to spread the wake hits) and real cambered blades.

## Superseded design (6th pass, 2026-11-08): simplified, 8 different parts and 9 pieces

The owner asked for a much simpler design (sketches confirmed in the session before modelling). The 5th pass had
20 different parts and 48 pieces. Changes, each removing parts rather than adding fixes:

- **No tie rods or nuts.** A perforated frame, screwed to the base, holds the filter, and the fan head sits on
  its top rim. The frame's height sets how much the comb beads are squeezed (0.5 mm at each end).
- **Comb and gasket in one.** Each comb is printed in TPU with two sealing beads on its outer face. There is no
  foam tape.
- **One fan head.** Inlet plate, fan housing, stator and nacelle are one part, lifted off with the rotor and
  motor inside to change the filter.
- **Direct drive.** The rotor (hub and 7 blades in one part) clamps straight onto the motor's 4 mm D shaft, and
  the motor screws into the cup floor (2 × M3, button heads in 2.5 mm counterbores). Shaft, two 608s, coupling,
  bracket and grommets are gone.
- **Feet printed into the base.**

| Part | What | z (assembly) |
| --- | --- | --- |
| `airmn_base` | 430 × 20 plate, 4 feet Ø20 × 5 underneath, comb groove 408 / 288 × 4, 5 M3 up into the frame flange (counterbores 6.5 × 3.5 underneath), PD pocket and cable channel | −5 .. 20 |
| `airmn_frame` | 430 / 422 × 453. Holes are 10 mm on an 11.2 hex pitch like the fan head's top: 120 column pairs × 43 rows, solid bands about 18 mm at both ends. Inner flange 422 / 410 × 8 at the bottom with 5 M3 taps on R208 | 20 .. 473 |
| `airmn_comb` ×2 (TPU) | Ring 406 / 292 × 10, zigzag slot 1.6 × 7, beads 404 / 401 and 297 / 294 × 1 on the outer face | low 15.5 .. 26.5; high (flipped) 462.5 .. 473.5 |
| `airmn_pleat_pack` | Unchanged | 19.5 .. 469.5 |
| `airmn_fan_head` | Spigot 421.6 / 412 × 5 into the frame, inlet flange 430 / 286 × 10 on the frame rim and the top beads, duct 404, 8 mm top with the hex grid inside R198. Motor cup 100 / 90: floor 5 (local 72), closed top at local 181. 11 flat placeholder vanes 3 × 60 from the cup to the duct wall | 468 .. 753 |
| `airmn_rotor` | Hub 100 × 40 (hub ratio 0.25, the lowest that keeps the blade roots working, for low noise), bore 4, M3 clamp 3 below the top (between two blades). 7 flat placeholder blades 3 thick to R200.5 (1.5 mm tip gap; true the printed rotor) | 499 .. 539 |
| `airmn_motor` | Shaft down, face on the cup floor; 6 mm of shaft in the rotor hub | 533 .. 620 |

Rotor to vanes: 50 mm (more than one blade height). 7 blades against 11 vanes share no factor. Unit height 753
plus 5 mm feet. Frame material: about 870 cm³ (about 1.1 kg PETG). The webs between holes are 1.2 mm, as in the
top grid.

Open items and risks:
- **Shaft engagement.** The motor's 4 mm shaft is *estimated* at 12 mm long, which leaves only 6 mm in the rotor
  hub. Check against the real motor. If the 400 mm rotor wobbles, add one 608 in the cup floor.
- **Even squeeze.** The fan head's weight is the only load on the top beads. If a smoke test shows a leak, add a
  quarter-turn bayonet at the rim.
- **Still to do:** real angled rotor blades and vanes, motor wires out through a vane, print-bed sector splits
  for the base, frame and fan head.

## 5th pass (2026-11-08): axial fan blowing up

Superseded by the 6th pass above. It also supersedes the plug-fan sections further down (kept as history). Basis: [upflow_feasibility.md](upflow_feasibility.md).
The filter (bottom cap, combs, gaskets, pack, feet, PD board) is unchanged.

| Part | What | z |
| --- | --- | --- |
| `airmn_inlet_plate` | 430 / 286 × 10, upper comb groove underneath, rod holes; open to the core | 474 .. 484 |
| `airmn_fan_housing` | 430 OD, 404 bore (the duct), 270 tall; rods run up through the 13 mm wall; 8 mm top with 1132 holes of 10 on a 11.2 hex pitch inside R198 (72 % open) as the vertical outlet; nut counterbores in the top | 484 .. 754 |
| `airmn_rotor_hub` | 176 × 40 on the 8 mm shaft, M3 clamp; flat underside (nose cone later) | 500 .. 540 |
| `airmn_rotor_blade` ×7 | **PLACEHOLDER**: flat radial plate R88 .. R199 (3 mm tip gap to the 404 bore), 3 × 40, no pitch | 500 .. 540 |
| `airmn_stator` | 11 flat guide vanes (placeholders too) between a 403 / 396 ring and the 180 centre-body hub; hub floor 20 holds two 608s and the grommet screws | 580 .. 640 (608s at 580, 593) |
| motor group | grommets 600, bracket 606 .. 641, coupling 610 .. 635, motor 629 .. 716 (shaft down) | inside the centre body |
| `airmn_nacelle` | 180 / 170 × 86 cap over the motor, closed top | 640 .. 726 |
| shaft / rods | Ø8 × 120 (500 .. 620); M5 × 752 (1 .. 753), top nuts in the housing top | |

Rotor–stator gap 40 (one blade height). 7 blades against 11 vanes and 5 rods share no factor. Unit height 754 + 5 mm
feet. Open items: real rotor blades (angled, from the feasibility sizing), stator ring fixing (screws into the
housing), a nose cone under the rotor hub, motor wires out through a vane.

## Decisions made with the owner (2026-11-08)

| Brief conflict / open point | Decision |
| --- | --- |
| Impeller blades 112 wide, but outlet slot 80 and top cap 120 tall | Keep 112 blades; taller slot and top cap (outlet band 162 tall, holes over 119 mm) |
| 450 pack + 120 top cap = 570, but "about 67 cm" | Thin 20 mm bottom cap. Top cover top at 816 |
| Tie rods: 3 through the centre sit in the inflow; 3 vs 9 blades gives a tone | 5 M5 rods outside the pack on R209 (5 and 9 share no factor) |
| Scope | Functional parts + assembly + exploded view. Print-bed sector splits and the pleating jig later |
| Look (2nd pass) | Clean 430 cylinder: dot-grid band flush with the caps, outside the rods; lid and pod replaced by a full-diameter top cover enclosing the motor |

Consequence of the rods outside: the caps are **430 across, not 400** (rod clears the comb by 4.5 mm).

## 3rd pass (2026-11-08): motor inside the filter, no exterior

At the owner's request, to confirm the internal assembly before designing the exterior:

- The motor group sits **inside the pack's open core**: a 5-spoke spider (ring 280 / 250 × 12, hub 80 × 40,
  two 608 seats) is screwed under the inlet ring with 5 M3 at R132.5; grommets, bracket, coupling and motor hang
  below it, motor shaft up. The 8 mm shaft runs from the impeller hub down through the eye into the spider.
- The outlet band, top cover and the old top bridge are **out of the assembly** (projects kept for later). The
  impeller is open above; tie rods now end on the inlet ring (489 long, top nuts 484 .. 488).
- Trade-off against the brief: the spider spokes and the motor now sit in the fan's inflow (the brief put them
  above the backplate). 5 spokes against 9 blades share no factor, and the spokes sit 23 mm below the shroud.

Layout of the core group (z): motor 318 .. 405 (shaft to 393), bracket 393 .. 428, coupling 399 .. 424,
grommets 428 .. 434, spider 434 .. 474 (608s at 434 and 467), shaft 414 .. 636. Unit height: 641 with feet.

## 4th pass: lid round the impeller, perforated top

- `airmn_impeller_housing`: 430 / 425 wall, 173 tall, seated in the inlet ring's rabbet (481 .. 654). Solid round
  the impeller; the 8 mm top plate carries 1969 holes of 7.2 on a 8.57 hex pitch inside R200 (62 % open over the
  grid), so the air leaves vertically, away from the inlet. 10 mm clearance over the impeller hub.
- Tie rods lengthened to 652 (1 .. 653); top nuts sit in Ø10 × 5 counterbores in the housing top.
- Unit height 654 + 5 mm feet.

## Main values

| Item | Value | Status |
| --- | --- | --- |
| Pleat pack | 120 pleats, folds at R200 / R150 (50 deep), 2.0 fold flats (wider than the 1.6 comb slot), 0.8 media, 450 tall | given (flats chosen) |
| Media area | 12.50 m of pleat line × 0.45 = 5.62 m² (brief: about 5.4) | check |
| Combs | Ring 406 / 292 × 10, zigzag slot 1.6 wide (0.4 clearance each side), 7 deep | chosen |
| Gaskets | Closed-cell foam 406 / 290 × 3, modelled uncompressed | chosen |
| Bottom cap | 430 × 20, comb groove 408 / 288 × 4, nut pockets 10 × 6, PD pocket 40 × 30 × 8 + 12 wide cable channel to the rim | chosen |
| Inlet ring | 430 / 240 × 10, comb groove underneath, outlet-band seat, stepped bellmouth 260→228→189 (lip 189 / 183 into the 195 eye, 3 mm radial gap) | eye given, steps chosen (no revolve in swlib) |
| Impeller | 300 OD, 195 eye, 9 flat blades 112 wide, 40° back from radial at the rim, from R100 to the rim | given |
| Blade | 3 thick, trailing edge tapered to 0.5 over 15, 2.6 tabs 3 deep into slots 3.0 wide in shroud and backplate | given (0.5 TE), rest chosen |
| Backplate | 300 × 4, integral hub 40 × 20 on the 8 mm shaft, M3 clamp screw | chosen (brief: printed or aluminium hub) |
| Outlet band | 430 / 425 × 162, flush with the caps, 1 mm outside the rods; holes 7.2 on a 8.57 hex pitch: 157 × 2 columns, 16 rows at 7.42 = 2512 holes, 64 % open over the hole zone; seats in 3 mm rabbets (Ø424) in the inlet ring and bridge | given (7.2, 64 %) |
| Band to impeller | 62 mm radial gap (band set out from the blade tips) | given rule |
| Bridge | 430 / 350 ring × 12 on the 5 rods, 5 spokes 20 wide, hub 80 × 40 with two 608 seats | chosen |
| Motor mount | Bracket on 4 silicone grommets 10 / 3.2 × 6 on the bridge hub, motor above it inside the top cover 430 / 424 × 167 (10 top, foam liner room above the motor; cooled by plenum air through the bridge openings) | given rule, sizes chosen |
| Motor | E-S Motor 25 mm gearhead BLDC, 24 V 600 rpm, run at 15 V: Ø25 × 75 body, 4 mm D shaft 12 long, M3 at 17 pitch | **estimated** (no drawing) |
| Coupling | Jaw coupling Ø20 × 25, bores 8 and 4 | estimated |
| Shaft | Ø8 × 88 steel, in two 608 bearings (grindmn_bearing_608 reused) | given |
| PD board | Adafruit HUSB238 #5807, 25.4 × 17.8 × 1.6 with USB-C | estimated |

## Layout (z, mm)

| Part | z |
| --- | --- |
| Feet | −5 .. 0 |
| Bottom cap | 0 .. 20 (groove 16 .. 20) |
| Lower gasket / comb | 16 .. 19 / 19 .. 29 (slots 22 .. 29) |
| Pleat pack | 22 .. 472 |
| Upper comb (flipped) / gasket | 465 .. 475 / 475 .. 478 |
| Inlet ring | 474 .. 484, bellmouth to 502 |
| Outlet band | 481 .. 643 (holes 497 .. 616) |
| Shroud / blades / backplate | 497 .. 500 / 497 .. 615 / 612 .. 616 (hub to 636) |
| Shaft | 612 .. 700 |
| Bridge | 640 .. 652, hub to 680; 608s at 640 and 673 |
| Grommets / bracket / coupling / motor | 680 .. 686 / 686 .. 721 / 690 .. 715 / 709 .. 796 |
| Top cover | 649 .. 816 (sits in the bridge's top rabbet) |
| Tie rods | 1 .. 815, nuts 1 .. 5 (bottom pockets) and 810 .. 814 (top counterbores) |

## Left out of this pass

Print-bed sector splits with keys and M3 screws; pleating jig; lid microswitch interlock; felt or foam
acoustic liner and the top cover's foam lining; filter seam overlap; motor wiring; fuse and LED; threads.
