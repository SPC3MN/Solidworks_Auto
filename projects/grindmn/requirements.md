# grindmn S: hand grinder in 13 parts

Source: the spcmn plan `plans/grindmn.md` (2026-11-06), redesigned on 2026-11-08 for **the simplest design that
works**: fewest parts, one load path, nothing that a part's own shape can do instead. Earlier layouts (bottom
dial, then top click adjuster) are in git history. Burr sizes are **assumed** until a 48 mm burr set is bought
and measured (section 2); every other value is **given**. Driving values live in `gen_projects.py`, which writes
each part project and both assemblies.

## 1. How it works

- **The shaft hangs from a nut.** An M6 × 0.75 nut on the shaft's top bears, through its Ø9 boss, on the top
  bearing's inner ring; the bearing sits in the bridge, whose flange sits on the tube's top face. Turning the nut
  clockwise (from above) lifts the shaft and the inner burr: finer.
- **One load path, no springs.** Gravity and the grinding load both push the shaft down, so the nut is always
  seated: burr → shaft → nut → top bearing → bridge flange → tube. A nylon thread patch in the nut gives it more
  friction than the top bearing's drag, so the setting cannot creep.
- **The crank cannot lift the burr.** It is a slip fit on the shaft's top flat and rests on the shaft's end;
  nothing holds it on, so nothing can pull the shaft up.
- **The burr holds itself.** The inner burr's D bore rests on the shoulder where the shaft's drive flats start:
  no collar, no clips. Above the burr the shaft steps down to Ø6, so the burr slides on from the top.
- **Stepless, read at the top.** 45 lines on the nut's chamfer, 16.7 µm a line, read against an index on the
  crank's boss (the crank is keyed to the shaft). Range 0 to 119 lines (1.98 mm, 2.64 turns); the gap between the
  crank and the nut shows the turn (3.0, 2.25, 1.5). Hold the crank, turn the nut: cup and crank stay on.
- **Grounds fall straight out** through the spider's Ø52 opening (three 4 mm spokes) into the cup.
- **Loading beans:** lift the crank off and pour through the bridge's three 10 mm openings. There is no lid.
- **Cleaning keeps the setting:** lift the crank off, then lift the bridge: the bridge, top bearing, nut, shaft
  and inner burr come out of the top in one piece (the burr passes the Ø50 hopper).

Axial datum: **z = 0 at the tube's bottom face, z up**, at grind 0 (burrs touching).

## 2. Buy and measure the burr set first

| Burr dimension | Assumed | How it is used |
|---|---|---|
| Outer burr OD × height | Ø54.00 × 20.0 | tube burr seat = measured OD + 0.005 / +0.015; burr at z 10 to 30 |
| Outer burr anti-rotation | 2 notches in the lower face, 4.4 wide, 2.3 deep, at 90° / 270° | the spider's tabs engage them. **If the bought burr has only OD flats:** two M4 grub screws through the tube at z 25 instead (2 more parts) |
| Inner burr base Ø × height | Ø47.6 × 30.0 | must pass the Ø50 hopper |
| Inner burr bore | 8 mm with two flats 6.5 across | the shaft's drive flats match; the burr rests where they start |
| Inner burr base at grind 0 | 1.0 above the outer burr's lower face | sets the flats' start (z 11) |

## 3. Parts

| # | Part | Make or buy | Material and finish |
|---|---|---|---|
| 1 | Tube | machine | 6061-T6, diamond knurl 0.8 pitch z 22 to 97, bead blast, clear anodise, seats masked |
| 2 | Bridge | machine | 6061-T6, clear anodise, bearing seat masked |
| 3 | Spider | machine | 6061-T6, clear anodise, bearing seat masked |
| 4 | Shaft | machine | 416 stainless, bearing seats ground |
| 5 | Nut | machine | 6061-T6, diamond knurl, clear anodise, thread masked, nylon patch |
| 6 | Crank arm | machine | 6061-T6, clear anodise |
| 7 | Catch cup | machine | 6061-T6, smooth, bead blast, clear anodise |
| 8, 9 | Burr set, 48 mm conical (inner and outer) | buy | stainless (section 2) |
| 10 | Ball bearing 608-2RS, 8 × 22 × 7 (lower) | buy | food-grade grease if available |
| 11 | Ball bearing 626-2RS, 6 × 19 × 6 (top) | buy | |
| 12 | O-ring 58 × 2, NBR 70 or FKM, food grade | buy | holds the cup |
| 13 | Revolving handle, aluminium, M6 stud (*model unverified*) | buy | |

Fits are ISO 286. Unless a table says otherwise: linear ±0.1, ISO 2768-mK, outside edges R1, inside edges 0.3 ×
45°, Ra 1.6 on fits, Ra 3.2 elsewhere before blasting.

## 4. Tube (part 1)

Stock 6061-T6 bar Ø70. Length **99.0**, outside **Ø64.00**. **Every seat is bored from the bottom in one chucking**
(op 10), so the spider, burr and bridge seats are concentric by construction; datum **A** is the burr seat.

| z from | z to | Feature | Size | Tolerance |
|---|---|---|---|---|
| 0 | 10.0 | spider seat | Ø56.000 | **H7**; runout 0.010 to A |
| 10.0 | 30.0 | outer burr seat | Ø54.00 (**assumed**) | measured OD + 0.005 / +0.015 |
| 30.0 | | burr shoulder | 2.0 radial | ⊥ 0.01 to A |
| 30.0 | 89.0 | hopper | Ø50.0 | ±0.05 |
| 89.0 | 99.0 | bridge seat (same bore, finish pass) | Ø50.000 | **H7**; runout 0.010 to A |
| 0 | 20.0 | outside spigot for the cup | Ø61.00 | **h8** |
| 12.0 | 14.70 | O-ring groove | Ø57.90 floor, 2.70 wide | wall behind it 1.95 (the thinnest spot) |
| 99.0 | | top face (the bridge flange sits on it) | | ⊥ 0.02 to A |

Ops: 10 lathe (face, OD, spigot, groove, all bores; part off at 99.5), 20 lathe soft jaws (face the top to 99.0,
knurl z 22 to 97), 30 finishing. No holes. Mass about 290 g.

## 5. The other machined parts

| Part | Sizes | Fits and notes |
|---|---|---|
| **Bridge** (z 91 to 103) | pilot Ø50 × 8, flange Ø64 × 4, hub Ø26, ring ID Ø46, 3 spokes × 4 at 60/180/300°: 10 mm bean openings | pilot **g6**; 626 seat Ø19 **J6** × 6 bored from the top, lip hole Ø15; runout 0.005 to the pilot |
| **Spider** (z −5 to 12) | ring Ø56 / 52 × 10 (z 0 to 10), hub Ø30 × 10 (z −5 to 5), 3 spokes × 4 at 0/120/240°, 2 tabs r 26 to 26.9 × 4 × 2 at 90/270° | ring **p6**, pressed in until it meets the outer burr; 608 seat Ø22 **J6** × 7 from below, lip hole Ø14 |
| **Shaft** (z −5 to 129, length 134; z_s from its bottom end) | Ø8 z_s 0 to 46, Ø6 above | Ø8 **h5** z_s 0 to 9 (lower seat + 2 of travel); flats 6.50 across z_s 16 to 46 with a square shoulder at 16; Ø6 **h5** z_s 102 to 110 (top seat); M6 × 0.75 z_s 111 to 121; flat 5.20 across z_s 121 to 134 |
| **Nut** (z 103 to 113) | Ø28 × 7 body on a Ø9 × 3 boss | M6 × 0.75 **6H**, nylon patch; 45 lines on the top chamfer, every fifth numbered |
| **Crank arm** (z 116 to 130) | 8 plate, 16 wide at the hub to 12 at the handle, R 85; Ø16 × 6 boss below | blind D bore Ø6 **H8** with the 5.20 flat, 13 deep (rests on the shaft's end); index line on the boss; M6 tapped for the handle |
| **Catch cup** (z −49 to 20) | Ø64 × 69; sleeve Ø61.20 × 20; chamber Ø58 × 45 (about 119 ml); base 4, inside R2 | sleeve **H8**; stops on the tube's bottom face; rim 1 × 30° lead-in for the O-ring |

## 6. Where every part sits (assembly)

Tube z at grind 0. Toward grind 119 the shaft, inner burr, crank and handle move down by up to 1.98; nothing else
moves.

| Part | z bottom | z top |
|---|---|---|
| Catch cup | −49.0 | 20.0 |
| Spider (hub / tabs) | −5.0 | 12.0 |
| 608-2RS lower | −5.0 | 2.0 |
| Shaft | −5.0 | 129.0 |
| Outer burr | 10.0 | 30.0 |
| Inner burr | 11.0 | 41.0 |
| O-ring | 12.35 | 14.35 |
| Tube | 0 | 99.0 |
| Bridge | 91.0 | 103.0 |
| 626-2RS top | 97.0 | 103.0 |
| Nut | 103.0 | 113.0 |
| Crank arm | 116.0 | 130.0 |
| Handle (at x 85) | 122.0 | 160.0 |

Overall 127 × 64 × 209 mm. Checked in FreeCAD (`python3 scripts/assembly.py assemblies/grindmn`): 13 components,
no interference other than nominal threads (nut on the shaft, handle stud in the arm) and the O-ring squeeze, at
grind 0 and at grind 119.

## 7. Assembly order

1. Outer burr up into its seat against the shoulder, notches at 90/270°.
2. Lower 608 into the spider from below; press the spider into the tube until its tabs seat in the burr's notches.
3. Cartridge: 626 into the bridge from above. Inner burr onto the shaft from the top, down to the flats' shoulder.
   Shaft up through the 626; nut on.
4. Lower the cartridge into the tube: burr down the hopper, shaft end into the lower bearing, bridge pilot into
   its seat.
5. Hold the shaft (or the crank on it) and turn the nut until the burrs just touch when turned by hand: grind 0.
   On the first build, etch line 0 opposite the crank's index there.
6. Crank on, O-ring on, cup on.

## 8. Marking

| Where | What |
|---|---|
| Nut top chamfer | 45 lines, 0 to 40 numbered; `16.7 µm` |
| Crank boss | index line |
| Tube, smooth band z 2 to 10 | `grindmn` |
| Cup base | grindmn mark, version, date and serial, in Plex Mono |

## 9. Numbers to check on the first build

| Check | Target | How |
|---|---|---|
| Inner burr runout at its base | ≤ 0.02 | dial indicator through the bottom with the cup off |
| Travel per line | 16.7 µm ± 1 | indicator on the shaft's end over one turn: 0.750 ± 0.02 |
| Setting holds | no creep over 30 g | grind, re-read the scale |
| Setting kept after cleaning | same line | lift the cartridge out and back |
| Mass | about 0.7 kg with burrs | scale |

## 10. Decisions

| # | Decision | Why | Cost |
|---|---|---|---|
| 1 | Stepless nut at the top, no clicks (owner, 2026-11-08) | removes the click disc, plunger and spring | no tactile steps; set by the scale |
| 2 | Shaft hung from the nut, no spring | gravity and grinding load already seat it | none found |
| 3 | Crank slip fit, no magnet | nothing can lift the burr | the crank falls off if the grinder is tipped |
| 4 | Burr seated on the shaft's own flats; shaft stepped to Ø6 above | removes the collar and both clips | top bearing is a 626, not a second 608 |
| 5 | No lid | one part fewer | a few beans may hop at the start |
| 6 | Knurled body, smooth flush cup (owner, 2026-11-08) | grip; one smooth silhouette | overrides "bodies are never knurled" |
| 7 | No hue | grindmn is archived (2026-11-05) | |
