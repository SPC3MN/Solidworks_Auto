# grindmn: hand grinder, every part for machining and modelling

Source: the spcmn plan `plans/grindmn.md` in spcmn-studio/spcmn (2026-11-06), redesigned on 2026-11-08 for
**top adjustment and the fewest parts** (owner's direction: "simplify the design as much as possible"). The
bottom-adjust version (grind dial threaded into the tube) is in git history before this change. Burr sizes are
marked **assumed** until a 48 mm burr set is bought and measured (section 2); every other value is **given**.
Each part is its own `projects/grindmn_<part>/`; the changed ones are written by `gen_projects.py`.

---

## 1. How it works

- **The shaft hangs from the top.** An adjuster nut screws onto an M8 × 0.75 thread at the top of the shaft and
  sits on a click disc, which sits on the top bearing's inner ring. The top bearing sits in the bridge, and the
  bridge's flange sits on the tube's top face. Turning the nut clockwise (seen from above) lifts the shaft and the
  inner burr: finer.
- **One load direction.** A spring under the top bearing pulls the shaft down, so the nut is always seated (about
  31 N at grind 0, 25 N at the coarsest setting). Grinding pushes the inner burr down too. Every load goes the same
  way, from the nut through the bearing into the bridge and the tube's top face: no backlash.
- **The crank cannot lift the burr.** The crank hub is held on the shaft's top end by a magnet that lets go at
  about 10 N, well under the spring's 25 N. Pulling up on the crank takes the crank off before the burr moves.
- **The numbers.** M8 × 0.75 with 45 clicks a turn: **16.7 µm a click**. 0 is where the burrs touch. Range 0 to
  119 clicks (1.98 mm, 2.64 turns). The dial is at the top: it can be read and turned with the crank and the
  cup on (hold the crank, turn the nut).
- **Grounds fall straight out.** Under the burrs there is only the lower-bearing spider: a Ø52 opening (the burrs
  exit at about Ø48) crossed by three 4 mm spokes. No ledge, nothing to clear.
- **Loading beans:** pull the crank off, lift the lid ring over the nut, pour about 30 g through the bridge's
  three 9 mm openings.
- **Cleaning keeps the setting:** crank off, lid off, lift the bridge out. The bridge, shaft, inner burr, spring,
  click disc and nut come out of the top as one cartridge (the inner burr passes the Ø50 hopper), and the nut never
  turns, so the grind setting is unchanged when it drops back in.

Axial datum for this note: **z = 0 at the tube's bottom face, z up**, everything at grind 0 (burrs touching).

## 2. Buy and measure the burr set first

The burr set is the one part whose sizes this note cannot know. Buy a **48 mm stainless conical burr set** sold as a
replacement for 48 mm hand grinders (sets for 1Zpresso K-series, Kingrinder K-series and their clones are the common
ones; *unverified* which fit best), then measure and replace the assumed values below.

| Burr dimension | Symbol | Assumed | How it is used |
|---|---|---|---|
| Outer burr (ring) outside diameter | D_ob | 54.00 | tube burr seat = D_ob + 0.005 to 0.015 |
| Outer burr height | H_ob | 20.0 | burr seat length; screw position |
| Outer burr anti-rotation features | | 2 flats on the OD | where the two M4 screws land |
| Inner burr (cone) base diameter | D_ib | 47.6 | must pass the Ø50 hopper (cleaning lifts it out the top) |
| Inner burr height | H_ib | 30.0 | shaft burr section length; e-clip groove |
| Inner burr bore and drive | | 8 mm with two flats 6.5 across | shaft drive section is cut to match |
| Inner burr base, resting at grind 0 | | 1.0 above the outer burr's lower face | sets the collar position |

If D_ob comes out above about 56 mm, step the spider seat, burr seat and outside up by the same amount.

## 3. Parts

| # | Part | Qty | Make or buy | Material and finish |
|---|---|---|---|---|
| 1 | Tube | 1 | machine | 6061-T6, **diamond knurl 0.8 pitch from z 22 to 97**, bead blast, clear anodise type II, fits masked |
| 2 | Bridge (top bearing carrier) | 1 | machine | 6061-T6, clear anodise, bearing seat masked |
| 3 | Spider (lower bearing carrier) | 1 | machine | 6061-T6, clear anodise, bearing seat masked |
| 4 | Shaft | 1 | machine | 416 stainless (magnetic, for the crank magnet), ground at the bearing seats |
| 5 | Crank arm | 1 | machine | 6061-T6 plate 6 mm, clear anodise |
| 6 | Crank hub | 1 | machine | 6061-T6, clear anodise, bore masked |
| 7 | Crank knob | 1 | machine | 6061-T6, diamond knurl, clear anodise |
| 8 | Lid ring | 1 | machine | 6061-T6, clear anodise |
| 9 | Catch cup | 1 | machine | 6061-T6, **smooth**, bead blast, clear anodise |
| 10 | Inner-ring spacer | 1 | machine | 303 stainless |
| 11 | Click disc | 1 | machine | 303 stainless |
| 12 | Adjuster nut (grind dial) | 1 | machine | 6061-T6, diamond knurl, clear anodise, thread masked (bare aluminium on the stainless thread: no galling) |
| 13 | Compression spring, stainless | 1 | buy | section 5.10 |
| 14 | Burr set, 48 mm conical | 1 set | buy | stainless (section 2) |
| 15 | Ball bearing 608-2RS, 8 × 22 × 7 | 2 | buy | food-grade grease fill if available |
| 16 | Retaining ring DIN 6799 size 6 (shaft 7–9 mm) | 2 | buy | stainless |
| 17 | Washer DIN 125-A 8.4 (8.4 × 16 × 1.6) | 1 | buy | A2 stainless |
| 18 | Button head screw ISO 7380 M4 × 6, 2.5 mm key | 2 | buy | A2; outer burr anti-rotation |
| 19 | Socket head screw ISO 4762 M3 × 10, 2.5 mm key | 2 | buy | A2; arm to hub (4 mm of thread in the hub) |
| 20 | Shoulder screw ISO 7379, Ø5 × 30 shoulder, M4 thread, 3 mm key | 1 | buy | A2 or 12.9 black; knob axle |
| 21 | Push-fit ball plunger, Ø4 body, Ø2 ball, smooth sleeve (*part number unverified*) | 1 | buy | stainless; the click |
| 22 | Flanged ball bearing MF105ZZ, 5 × 10 × 4 | 2 | buy | in the knob |
| 23 | O-ring 60 × 2, NBR 70 or FKM, food grade | 1 | buy | holds the catch cup |
| 24 | Disc magnet N52, Ø6 × 3, nickel plated | 1 | buy | holds the crank (pull about 10 N) |
| 25 | Dowel pin ISO 8734, 3 × 8 | 1 | buy | A1 stainless; keeps the bridge from turning |
| 26 | Food-safe grease (NSF H1) | | buy | shaft thread, plunger, knob axle |

Keys needed: 2.5 mm and 3 mm only. Fits are ISO 286. Unless a table says otherwise: linear ±0.1, angles ±0.5°,
general tolerance ISO 2768-mK, all machined edges 0.3 × 45° chamfer, Ra 1.6 on fits, Ra 3.2 elsewhere before
blasting.

Removed by the redesign: the grind dial (303 stainless, M58 × 1 thread, 60 click grooves), the tube's internal
thread, relief and pilot seat, the radial plunger hole, the bridge screw (M4 × 12) and its groove.

## 4. The tube (part 1)

Stock: **6061-T6 round bar Ø70**. Finished length **99.0**, outside **Ø64.00**.

### 4.1 Inside, from the bottom face up (all bored from the bottom, one chucking)

| z from | z to | Feature | Size | Tolerance | Notes |
|---|---|---|---|---|---|
| 0 | 10.0 | spider seat | Ø56.000 | **H7** (+0.030 / 0) | the spider is pressed in from below |
| 10.0 | 30.0 | outer burr seat (**assumed** H_ob) | Ø54.00 (**assumed** D_ob) | measured OD + 0.005 / +0.015 | |
| 30.0 | | burr shoulder | flat face, 2.0 radial | ⊥ 0.01 to datum A | the outer burr bears up on it |
| 30.0 | 89.0 | hopper | Ø50.0 | ±0.05 | Ra 3.2 |
| 89.0 | 99.0 | bridge seat (same bore, finish pass) | Ø50.000 | **H7** (+0.025 / 0) | the bridge pilot is 8 long |

### 4.2 Outside and top face

| z from | z to | Feature | Size | Tolerance |
|---|---|---|---|---|
| 0 | 99.0 | body | Ø64.00 | ±0.02 (before knurling) |
| 22.0 | 97.0 | diamond knurl, 0.8 pitch | | starts above the cup rim (z 20) |
| 12.0 | 14.70 | O-ring groove (catch cup) | Ø60.90 floor, 2.70 wide | floor ±0.05, width +0.1 / 0 |
| 99.0 | | top face | flat; the bridge flange sits on it | ⊥ 0.02 to datum A |
| 93.0 | 99.0 | dowel hole, r 28.5 at 0° | Ø3 **H7**, 6 deep (the ISO 8734 m6 pin is a light press) | |

Datum **A** is the outer burr seat Ø54. Spider seat and bridge seat: circular runout 0.010 to A.

### 4.3 Radial holes (second operation)

| Hole | z | Angle | Size |
|---|---|---|---|
| Outer burr screws | 25.0 (**assumed**, on the burr's flats, above the cup rim) | 90°, 270° | M4 × 0.7 tapped through the 5 mm wall |

### 4.4 Operations

| Op | Machine | Work |
|---|---|---|
| 10 | Lathe, bar in chuck | Face the bottom. Turn the OD Ø64. Cut the O-ring groove. Drill and rough bore. Rest. Finish bore the hopper and bridge seat (one bar, spring pass), burr seat and shoulder, spider seat. Part off at 99.5. **Every seat comes from this one chucking.** |
| 20 | Lathe, soft jaws | Face the top to 99.0 (the bridge's axial seat; grind 0 is set after assembly, so its height is not critical). Knurl z 22 to 97. |
| 30 | Mill | Drill and tap the two M4 holes; drill and ream the dowel hole. |
| 40 | Finishing | Bead blast, mask the seats, clear anodise. Laser-etch the marks (section 8). |

Mass: about 300 g.

## 5. The other parts

### 5.1 Bridge (part 2)

Stock 6061-T6 bar Ø70 × 15. z_b from the bridge's bottom face; at assembly z_b 0 = tube z 91.

| Feature | Size | Tolerance |
|---|---|---|
| Pilot ring, z_b 0 to 8 | Ø50.000 OD, Ø46 ID | **g6** (−0.009 / −0.025) in the H7 seat |
| Flange, z_b 8 to 12 | Ø64 OD, Ø46 ID; underside sits on the tube's top face | underside ⊥ 0.01 to the pilot |
| Hub | Ø28 OD, Ø18.5 hole | |
| Bearing seat (608), bored from the **top** | Ø22.000 × 7.0 deep (z_b 5 to 12), lip below it | **J6**; runout 0.005 to the pilot |
| Spokes | 3 × 4.0 wide, full height, at 60°, 180°, 300° | |
| Bean openings | between the Ø28 hub and the Ø46 ring: 9 mm wide | |
| Dowel hole | Ø3.1 through the flange at r 28.5, 0° | |

Mass: about 36 g.

### 5.2 Spider (part 3)

Stock 6061-T6 bar Ø60 × 18. z_sp from its bottom face; at assembly z_sp 0 = tube z −5.

| Feature | Size | Tolerance |
|---|---|---|
| Ring, z_sp 5 to 15 | Ø56 OD, Ø52 ID | **p6** press in the H7 seat; top face presses the outer burr up against its shoulder |
| Hub, z_sp 0 to 10 | Ø30 OD, Ø14 hole above the seat | |
| Bearing seat (608), bored from the bottom | Ø22.000 × 7.0 deep | **J6**; runout 0.005 to the ring OD |
| Spokes | 3 × 4.0 wide, z_sp 5 to 10, at 0°, 120°, 240° | |

The lower bearing carries no axial load: the shaft slides in its inner ring (h5 seat) as the grind changes.
Mass: about 22 g.

### 5.3 Shaft (part 4)

Stock: 416 stainless bar Ø10. Turn between centres, grind both bearing seats in one setup. z_s from the bottom
end; at grind 0 z_s 0 = tube z −5.

| z_s from | z_s to | Feature | Size | Tolerance |
|---|---|---|---|---|
| 0 | 13.0 | lower bearing seat (bearing at z_s 0 to 7, slides to 2 to 9 at grind 119) | Ø8.000 | **h5**, Ra 0.4 |
| 13.0 | 16.0 | collar, the inner burr sits on it | Ø10.0 | both faces ⊥ 0.01 |
| 16.0 | 46.0 | burr drive (**assumed** H_ib) | Ø8.0, two flats 6.50 across | flats ±0.02 |
| 46.2 | 46.94 | e-clip groove (holds the burr down) | Ø6.0, 0.74 wide | |
| 82.0 | 82.74 | e-clip groove (spring seat) | Ø6.0, 0.74 wide | |
| 101.0 | 110.0 | top bearing seat (7 long + 2 of travel) | Ø8.000 | **h5**, Ra 0.4 |
| 110.0 | 138.0 | flat 7.20 across (click disc and crank hub) | | ±0.02 |
| 113.0 | 127.0 | thread M8 × 0.75, single start, right hand | | 6g |
| 138.0 | | top end, 0.3 chamfer, face flat (the magnet sits on it) | | |

Length 138.0. Runout of both seats to each other 0.005. Mass: about 53 g.

### 5.4 Click disc (part 11) and adjuster nut (part 12)

| Part | Feature | Size |
|---|---|---|
| Click disc | Ø30 × 3 disc on a Ø11.5 × 2 boss (the boss bears on the bearing's inner ring only) | 303 stainless |
| | Bore | Ø8 **H8**; the disc's 3 mm has the 7.20 flat (+0.03 / +0.01) |
| | Click grooves on the top face | 45 radial, 90° V, 0.84 deep, from r 9 to the rim, 8.000° pitch |
| Adjuster nut | Ø30 × 10, diamond knurl | 6061-T6 |
| | Thread | M8 × 0.75, 6H |
| | Plunger hole | Ø4 **H7** through at r 12; the plunger's Ø2 ball reaches the disc's grooves |
| | Scale | 45 lines on the top chamfer, every fifth numbered 0, 5 … 40; index line on the click disc |

The disc turns with the shaft (flat); the nut turns against it. 0 is wherever the burrs touch: on the first
build, etch line 0 of the scale opposite the disc's index at that point (single-start thread, so it repeats).
Turns: the gap between the nut and the crank hub is 3.0 at turn 0, 2.25 after one turn, 1.5 after two.

### 5.5 Inner-ring spacer (part 10)

303 stainless, Ø11.5 × Ø8.2 × 2.0, faces parallel 0.01. Lets the spring press on the top bearing's inner ring only.

### 5.6 Crank hub (part 6) and arm (part 5)

Unchanged from the bottom-adjust design: hub Ø18 × 19, bore Ø8 H8 with the 7.20 flat 12 deep, magnet pocket Ø6 × 3
above it, a 14 wide × 3 deep arm slot across the top, two M3 tapped 6 deep, 12 apart. Arm 6 plate, 100 long, 14 to
12 wide, crank radius 85.0, two Ø3.4 holes at the hub end (plain: at 12 mm spacing a counterbore would break out of
the arm's end), M4 tapped at the knob end. **M3 × 10** screws: heads 3 proud of the arm, 4 mm of thread in the hub.
Hub bottom to nut top: 3.0 at grind 0, 1.0 at grind 119.

### 5.7 Crank knob (part 7)

Unchanged: 6061-T6, Ø20 × 28.4, diamond knurl 0.8 pitch, Ø10 H7 × 4 deep at each end for the two MF105ZZ, on the
ISO 7379 Ø5 × 30 shoulder screw.

### 5.8 Lid ring (part 8)

6061-T6, Ø64 × Ø32 × 3.0, sits on the bridge flange around the click disc (1 mm radial play) and lifts off over the
Ø30 nut once the crank is off. It covers the bean openings outside r 16; the nut and disc cover the rest.

### 5.9 Catch cup (part 9)

| Feature | Size | Tolerance |
|---|---|---|
| Outside | Ø68.0 × 69.0, smooth | |
| Sleeve bore, from the rim | Ø64.20 × 20.0 deep | **H8** (+0.046 / 0) |
| Grounds chamber | Ø60.0 × 45.0 deep (about 125 ml) | |
| Base | 4.0 thick, inside corner R2 | |
| Rim | 1.0 × 30° lead-in, so the O-ring is not cut | |

The cup slides over the tube's bottom onto the O-ring at z 13.35 and its internal step stops on the tube's bottom
face. It no longer covers anything that is adjusted.

### 5.10 Spring (part 13)

| Property | Value |
|---|---|
| Material | stainless 302/304 |
| Outside | 11.5 to 12.0 max |
| Inside | 8.5 min (clears the Ø8 shaft) |
| Free length | about 25 |
| Installed length | 14.7 at grind 0, 16.7 at grind 119 |
| Rate | 3 N/mm (about 4.7 active coils of 1.2 wire on a 10.8 mean diameter) |
| Force | about 31 N at grind 0, 25 N at grind 119: at least 2.5 × the magnet's pull |
| Solid length | under 11 |

Stack from the bottom: e-clip (shaft groove at z_s 82.0), washer, spring, spacer, top bearing's inner ring.

## 6. Where every part sits (for the assembly model)

Tube z, at grind 0. At grind 119 the shaft side (shaft, inner burr, e-clips, washer, crank hub, magnet, arm,
screws, knob stack) is 1.98 lower and the spring is 1.98 longer; everything else does not move.

| Part | z bottom | z top |
|---|---|---|
| Catch cup (base outside) | −49.0 | 20.0 (rim) |
| Spider | −5.0 | 10.0 |
| Lower 608-2RS | −5.0 | 2.0 |
| Shaft | −5.0 | 133.0 |
| Outer burr | 10.0 | 30.0 |
| Inner burr | 11.0 | 41.0 |
| Burr e-clip | 41.2 | 41.9 |
| Spring e-clip, washer | 77.0 | 79.3 |
| Spring | 79.3 | 94.0 |
| Spacer | 94.0 | 96.0 |
| Bridge | 91.0 | 103.0 |
| Top 608-2RS | 96.0 | 103.0 |
| Tube | 0 | 99.0 |
| Lid ring | 103.0 | 106.0 |
| Click disc | 103.0 | 108.0 |
| Adjuster nut | 108.0 | 118.0 |
| Crank hub | 121.0 | 140.0 |
| Crank arm | 137.0 | 143.0 |
| Knob (on the arm, 85.0 off the axis) | 143.8 | 172.2 |

Overall: 225.5 mm from the cup's base to the top of the knob's shoulder screw, Ø68 at the cup. Checked in FreeCAD
(`scripts/assembly.py assemblies/grindmn --backend freecad`): no interference other than nominal threads in
tap-drill holes, the O-ring squeeze and the plunger ball, at grind 0 and at grind 119.

## 7. Assembly order

1. Fit the outer burr up into its seat against the shoulder; fit the two M4 × 6 screws into its flats.
2. Press the lower 608-2RS into the spider from below. Press the spider into the tube's bottom until it meets the
   outer burr.
3. Press the dowel into the tube's top face.
4. Cartridge: press the top 608-2RS into the bridge from above. On the shaft, from the top end: inner burr down
   onto the collar, e-clip above it; e-clip at z_s 82, washer, spring, spacer. Push the shaft up through the
   bridge's bearing (the spring compresses), slide the click disc onto the flat, grease the thread and start the
   nut.
5. Lower the cartridge into the tube: the inner burr goes down the hopper, the shaft's bottom end into the lower
   bearing, the bridge pilot into its seat with the flange over the dowel.
6. Hold the crank hub's flat (or the shaft) and turn the nut clockwise, clicking, until the burrs just touch when
   the shaft is turned by hand. That is grind 0. On the first build, etch line 0 opposite the disc's index.
7. Lid ring on, crank on (the magnet holds it), O-ring on, catch cup on.

Cleaning: crank off, lid off, lift the bridge out with everything on the shaft. Nothing else comes apart, and the
setting is kept.

## 8. Marking

| Where | What |
|---|---|
| Tube OD, smooth band z 2 to 10 | `grindmn`, the index line at 0° |
| Tube OD at z 25, beside the burr screws | `48 mm conical` |
| Adjuster nut top chamfer | 45 lines, 0 to 40 numbered; `16.7 µm / click` |
| Click disc rim | index line |
| Catch cup base | grindmn mark, model version, build date and serial, in Plex Mono |

The mn dot grid moves off the body (now knurled) to the catch cup's base.

## 9. Numbers to check on the first build

| Check | Target | How |
|---|---|---|
| Inner burr runout at its base | ≤ 0.02 | dial indicator through the bottom with the cup off |
| Axial travel per click | 16.7 µm ± 1 | dial indicator on the shaft's top end over 45 clicks: 0.750 ± 0.02 mm |
| Setting kept after cleaning | same click | lift the cartridge out and back, re-check grind 0 |
| Crank pull-off force | under 15 N, burr does not move | spring scale on the knob, dial indicator on the shaft |
| Mass | about 0.85 kg with burrs | scale |

## 10. Assumptions and decisions

| # | Item | Why | If it changes |
|---|---|---|---|
| 1 | The burr sizes in section 2 | only the bought burr set can tell | burr seat, spider, collar, groove positions |
| 2 | Top adjustment, shaft hung from a nut on the top bearing (owner, 2026-11-08) | dial visible and usable with the cup on; one load direction; fewer and simpler parts | — |
| 3 | M8 × 0.75, 45 clicks (16.7 µm) | standard fine thread; 45 grooves leave room for a Ø2 ball on a Ø30 disc (60 would not) | 60 clicks on M8 × 1 needs a larger disc |
| 4 | Knurled body (owner, 2026-11-08) | grip; overrides the design language's "bodies are never knurled" | etched dot grid instead |
| 5 | Magnet crank, spring 2.5 × the magnet's pull | crank pulls off without a tool and cannot lift the burr | an M4 screw in the shaft end would need a much stiffer spring |
| 6 | Catch cup on an O-ring, not threaded | a thread at the bottom would leave under 1.5 mm of wall | |
| 7 | No hue | grindmn is archived (2026-11-05) | a revival needs a colour decision |
