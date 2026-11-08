# airmn bench prototype: requirements

Source: spcmn design brief `plans/airmn-prototype-brief.md` (spcmn-studio/spcmn, 2026-11-08), a copy of the
Claude Doc "airmn prototype: design brief". Values from the brief are **given**. Values the engineer has to
choose are **chosen** here, and sizes of bought parts not in the brief are **estimated**.

Geometry: `airmn_parts.py` (one function per part, volumes by hand). Values: `gen_projects.py`, which writes
every `projects/airmn_<part>/` project and both assemblies. Axis: z up, z = 0 at the bottom cap's underside, the
unit's axis on the origin.

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
