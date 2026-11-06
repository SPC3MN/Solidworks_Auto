# grindmn: hand grinder, every part for machining and modelling

Source: the spcmn plan `plans/grindmn.md` in spcmn-studio/spcmn (2026-11-06), copied here as this project's
requirements. Nothing is modelled yet: each part below becomes its own `projects/grindmn_<part>/` (or one assembly)
when it is built. Burr sizes are marked **assumed** (estimated) until a 48 mm burr set is bought and measured (section 2); every other
value is **given**.

---

## 1. How it works

- **One tube, three seats.** The aluminium tube holds the top bearing (in a bridge), the outer burr and the grind
  dial. All three seats, the dial thread and the outside are cut in **one lathe chucking, from the bottom end**, so
  they are concentric to each other by construction. Every seat steps smaller going up, which is what makes one
  setup possible.
- **The shaft is held from below.** The 8 mm shaft runs in two 608-2RS bearings. A collar on the shaft sits on the
  lower bearing; the lower bearing sits in the **grind dial**, which screws into the bottom of the tube. Turning the
  dial moves the bearing, the shaft and the inner burr up or down together.
- **A spring keeps it seated.** A spring under the top bearing pushes the shaft down onto the lower bearing. Grinding
  pushes the inner burr down too, so every load goes the same way into the dial thread: no backlash, and the number
  stays true under load.
- **The numbers.** Dial thread M58 × 1, 60 clicks a turn: **16.7 µm of axial travel a click**, within the design
  language's 15 to 20 µm. Screw the dial in until the burrs touch: that is 0. The thread is single-start, so 0 falls
  at the same mark every time it is reassembled. Range: 0 to 119 clicks (2.0 mm, two turns).
- **Grounds** fall through the dial's three spokes into a catch cup that slides over the bottom of the tube and is
  held by an O-ring.
- **Loading beans:** pull the crank off (a magnet holds it), lift the lid, pour about 30 g through the bridge.

Axial datum for this note: **z = 0 at the tube's bottom face, z up**, everything shown at grind 0 (burrs touching).

## 2. Buy and measure the burr set first

The burr set is the one part whose sizes this note cannot know. Buy a **48 mm stainless conical burr set** sold as a
replacement for 48 mm hand grinders (sets for 1Zpresso K-series, Kingrinder K-series and their clones are the common
ones; *unverified* which fit best), then measure and replace the assumed values below. Every dimension that depends on
them is marked **assumed** in the tables.

| Burr dimension | Symbol | Assumed | How it is used |
|---|---|---|---|
| Outer burr (ring) outside diameter | D_ob | 54.00 | tube burr seat = D_ob + 0.005 to 0.015 |
| Outer burr height | H_ob | 20.0 | burr seat length; screw position |
| Outer burr anti-rotation features | | 2 notches on the OD or lower face | where the two M4 screws land |
| Inner burr (cone) base diameter | D_ib | 48.0 | must pass the 50 mm hopper bore |
| Inner burr height | H_ib | 30.0 | shaft burr section length; e-clip groove |
| Inner burr bore and drive | | 8 mm with two flats 6.5 across | shaft drive section is cut to match |
| Inner burr base, resting at grind 0 | | 1.0 above the outer burr's lower face | sets the collar length |

If D_ob comes out above about 56 mm, the tube grows: keep the 2 mm hopper shoulder and the 4 mm wall at the
thread, and step every diameter in section 4 up by the same amount.

## 3. Parts

| # | Part | Qty | Make or buy | Material and finish |
|---|---|---|---|---|
| 1 | Tube | 1 | machine | 6061-T6, bead blast, clear anodise type II 10–15 µm, fits masked |
| 2 | Bridge (top bearing carrier) | 1 | machine | 6061-T6, clear anodise, bearing bore masked |
| 3 | Grind dial (lower bearing carrier) | 1 | machine | 303 stainless, bead blast, passivate |
| 4 | Shaft | 1 | machine | 416 stainless (magnetic, for the crank magnet), ground at the bearing seats |
| 5 | Crank arm | 1 | machine | 6061-T6 plate 6 mm, clear anodise |
| 6 | Crank hub | 1 | machine | 6061-T6, clear anodise, bore masked |
| 7 | Crank knob | 1 | machine | 6061-T6, diamond knurl, clear anodise |
| 8 | Lid | 1 | machine | 6061-T6, clear anodise |
| 9 | Catch cup | 1 | machine | 6061-T6, bead blast, clear anodise |
| 10 | Inner-ring spacer | 1 | machine | 303 stainless |
| 11 | Burr set, 48 mm conical | 1 set | buy | stainless (section 2) |
| 12 | Ball bearing 608-2RS, 8 × 22 × 7 | 2 | buy | food-grade grease fill if available |
| 13 | Compression spring, stainless | 1 | buy | section 5.10 |
| 14 | Retaining ring DIN 6799 size 6 (shaft 7–9 mm) | 2 | buy | stainless |
| 15 | Washer DIN 125-A 8.4 (8.4 × 16 × 1.6) | 1 | buy | A2 stainless |
| 16 | Button head screw ISO 7380 M4 × 6, 2.5 mm key | 2 | buy | A2; outer burr anti-rotation |
| 17 | Button head screw ISO 7380 M4 × 12, 2.5 mm key | 1 | buy | A2; bridge anti-rotation |
| 18 | Socket head screw ISO 4762 M3 × 8, 2.5 mm key | 2 | buy | A2; arm to hub |
| 19 | Shoulder screw ISO 7379, Ø5 × 30 shoulder, M4 thread, 3 mm key | 1 | buy | A2 or 12.9 black; knob axle |
| 20 | Flanged ball bearing MF105ZZ, 5 × 10 × 4 | 2 | buy | in the knob |
| 21 | Push-fit ball plunger, Ø5 body, Ø3 ball, smooth sleeve (Kipp K0328 or equivalent, *unverified*) | 1 | buy | stainless; the click |
| 22 | O-ring 60 × 2, NBR 70 or FKM, food grade | 1 | buy | holds the catch cup |
| 23 | Disc magnet N52, Ø6 × 3, nickel plated | 1 | buy | holds the crank |
| 24 | Food-safe grease (NSF H1) | | buy | dial thread, plunger, knob axle |

Keys needed: 2.5 mm and 3 mm only, as the design language asks. The ball plunger is pressed in and has no key.

Fits are ISO 286. Unless a table says otherwise: linear ±0.1, angles ±0.5°, general tolerance ISO 2768-mK, all
machined edges 0.3 × 45° chamfer (one edge rule), Ra 1.6 on fits, Ra 3.2 elsewhere before blasting.

## 4. The tube (part 1)

Stock: **6061-T6 round bar Ø70**, cut long enough to hold in the chuck (about 130 + chuck grip), or one long bar
with parts parted off. Finished length **122.0**, outside **Ø64.00**.

### 4.1 Inside, from the bottom face up (all bored from the bottom)

| z from | z to | Feature | Size | Tolerance | Notes |
|---|---|---|---|---|---|
| 0 | 1.0 | entry chamfer | to Ø59.0 | | 30° lead for the thread |
| 0 | 10.0 | dial thread | M58 × 1, internal | 6H | single-start, right-hand; minor Ø56.92 |
| 10.0 | 12.0 | thread relief | Ø59.0 | ±0.1 | runout groove for the threading tool |
| 12.0 | 30.0 | dial pilot seat | Ø56.000 | **H6** (+0.019 / 0) | sets the lower bearing's centre |
| 30.0 | 50.0 | outer burr seat (**assumed** H_ob) | Ø54.00 (**assumed** D_ob) | measured OD + 0.005 / +0.015 | |
| 50.0 | | burr shoulder | flat face, 2.0 radial | ⊥ 0.01 to datum A | the outer burr bears up on it |
| 50.0 | 111.0 | hopper bore | Ø50.0 | ±0.05 | Ra 3.2 |
| 111.0 | 119.0 | bridge seat | Ø44.000 | **H7** (+0.025 / 0) | |
| 119.0 | | bridge shoulder | flat face, 2.0 radial | ⊥ 0.01 to datum A | the bridge bears up on it |
| 119.0 | 122.0 | top lip, bean opening | Ø40.0 | ±0.05 | top face is the part-off face |

### 4.2 Outside

| z from | z to | Feature | Size | Tolerance |
|---|---|---|---|---|
| 0 | 122.0 | body | Ø64.00 | ±0.02, cylindricity 0.02 |
| 14.65 | 17.35 | O-ring groove (catch cup) | Ø60.90 floor, 2.70 wide | floor ±0.05, width +0.1 / 0 |
| 0 and 122 | | edges | 0.5 × 45° | |

### 4.3 Geometric tolerances

Datum **A** is the outer burr seat Ø54.

| Feature | Tolerance |
|---|---|
| Dial pilot seat Ø56 | circular runout 0.010 to A |
| Bridge seat Ø44 | circular runout 0.010 to A |
| Burr shoulder and bridge shoulder | perpendicularity 0.010 to A |
| Dial thread M58 × 1 | runout of the pitch diameter 0.03 to A |
| Outside Ø64 | runout 0.03 to A |
| Bottom face | perpendicularity 0.02 to A (the dial's index reads off it) |

### 4.4 Radial holes (second operation, on a mill)

Angles are around the tube, 0° at the index line.

| Hole | z | Angle | Size | Notes |
|---|---|---|---|---|
| Outer burr screws | 40.0 (**assumed**, mid burr) | 90°, 270° | M4 × 0.7 tapped through the 5 mm wall | set from the burr's notches |
| Bridge screw | 115.0 | 0° | M4 × 0.7 tapped through the 10 mm wall | screw tip enters the bridge's groove 2 mm |
| Ball plunger | 22.0 | 180° | Ø5 H7 through (to the plunger maker's press fit) | ball reaches the dial's grooves; flush with the OD |

### 4.5 Operations

| Op | Machine | Work |
|---|---|---|
| 10 | Lathe, bar in chuck, stick-out about 128 | Face the bottom. Turn the OD Ø64 over 124. Cut the O-ring groove. Drill and rough bore through to Ø38. Rough every bore 0.3 on diameter undersize. Let it rest (aluminium moves after roughing). Finish bore the bridge seat, top lip, hopper, burr seat and shoulder, pilot seat; cut the relief; single-point the M58 × 1 thread. Check the thread with a gauge or the dial itself. Part off at 122.5. **Every feature in section 4.3 comes from this one chucking.** |
| 20 | Lathe, soft jaws on the OD | Face the top to 122.0, chamfer the top edge and the lip. Nothing in this op is a datum. |
| 30 | Mill, tube in a V-block or 5C collet block | Drill and tap the three M4 holes; drill and ream the plunger hole. Deburr inside. |
| 40 | Finishing | Bead blast (glass bead, fine). Plug-mask the pilot seat, burr seat, bridge seat and thread. Clear anodise type II. |
| 50 | Laser | Etch the index line, the dot band and the part names (section 8). Press in the ball plunger. |

Tools for op 10: the bridge seat is 111 to 119 mm deep through a 50 mm bore. Use a Ø32 boring bar (steel shank
manages about 4 × overhang at light cuts; a carbide or damped bar is better), and finish all seats with the same tool
and a spring pass so they share one cut. Turn the OD in a light finishing pass at 128 stick-out (L/D about 2).

Mass: about 360 g.

## 5. The other parts

### 5.1 Grind dial (part 3)

Stock: 303 stainless bar Ø70 × 40. One lathe setup for the thread, pilot and bearing seat (same reason as the tube),
then the spokes and grooves on a mill with a rotary axis (or a lathe with live tooling and a C axis).

Axial datum: the dial's bottom face, z_d up. At grind 0 the dial's top face is at tube z = 28.0 and the flange sits
0.5 below the tube's bottom face.

| z_d from | z_d to | Feature | Size | Tolerance |
|---|---|---|---|---|
| 0 | 6.0 | grip flange | Ø63.4 before knurl, diamond knurl 0.8 pitch (about Ø63.7 after) | |
| 6.0 | 15.0 | thread | M58 × 1, external, single-start, right-hand | 6g |
| 15.0 | 16.5 | thread relief | Ø56.5 | ±0.1 |
| 16.5 | 34.5 | pilot | Ø56.000 | **h5** (0 / −0.013) |
| 0 | 34.5 | ring bore | Ø50.0 | ±0.1 |
| 24.5 | 34.5 | hub | Ø30 OD, joined to the ring by 3 spokes 5.0 wide, 10 tall, at 0°, 120°, 240° | |
| 27.5 | 34.5 | bearing seat (608), bored from the top | Ø22.000 | **J6** (+0.008 / −0.005) |
| 24.5 | 27.5 | bearing lip | Ø18.5 hole | the outer ring sits on it |

Pilot fit H6 / h5 gives 0 to 32 µm. The plunger pushes the pilot to one side, always the same side, so the
offset repeats.

Geometric: bearing seat runout 0.005 to the pilot; thread pitch diameter runout 0.03 to the pilot; bearing lip face
perpendicular 0.01 to the pilot.

Click grooves: 60 axial V-grooves, 90° included, 0.5 deep, on the pilot over z_d 16.5 to 34.5, equally spaced 6.000°
(±0.05° pitch). The plunger at tube z = 22.0 stays on the grooves over the whole 2 mm travel.

Scale: 60 lines laser-etched on the flange's top chamfer, every fifth line numbered 0, 5 … 55, in Plex Mono. Line 0
is set at assembly (section 7, step 9). The turn is read from the gap between the flange and the tube: under 1.5 mm
is turn 0, over 1.5 mm is turn 1 (add 60). Gap at grind 0: 0.5 mm; at 119: 2.48 mm.

Spokes: leave the most open area the stiffness allows. Three 5 mm spokes leave about 85% of the 50 mm ring open.

Mass: about 200 g.

### 5.2 Bridge (part 2)

Stock: 6061-T6 bar Ø50 × 15. One lathe setup for the OD and the bearing bore, then the spokes on a mill.

| Feature | Size | Tolerance |
|---|---|---|
| Outside | Ø44.000 | **h6** (0 / −0.016) |
| Thickness | 8.0 | ±0.05 |
| Hub | Ø30 OD | |
| Bearing seat (608), bored from the bottom | Ø22.000 × 7.0 deep | **J6** |
| Bearing lip at the top | 1.0 thick, Ø18.5 hole | the outer ring bears up on it |
| Spokes | 3 × 5.0 wide, full 8.0 thick, at 60°, 180°, 300° (between the dial's spokes, so the view down is open) | |
| Outer ring | 3.0 radial (Ø44 to Ø38) | |
| Screw groove | on the OD at 4.0 from the top, 2.0 wide, 1.0 deep, 15° arc at 0° | the M4 tip sits in it |
| Runout | bearing seat 0.005 to the OD; top face perpendicular 0.01 to the OD | |

Mass: about 15 g.

### 5.3 Shaft (part 4)

Stock: 416 stainless bar Ø10 (or Ø12 ground to size). Turn between centres, grind the two bearing seats in one
setup between centres.

Datum: the shaft's bottom end, z_s up. At grind 0 the bottom end is at tube z = 20.0, 1 mm below the lower bearing.

| z_s from | z_s to | Feature | Size | Tolerance |
|---|---|---|---|---|
| 0 | 8.0 | lower bearing seat (bearing at 1.0 to 8.0) | Ø8.000 | **h5** (0 / −0.006), Ra 0.4 |
| 8.0 | 11.0 | collar, sits on the lower bearing's inner ring (**assumed** length: puts the inner burr's base 1.0 above the outer burr's lower face) | Ø10.0 | ±0.02; both faces ⊥ 0.01 |
| 11.0 | 41.0 | burr drive (**assumed** H_ib) | Ø8.0 with two flats 6.50 across (**assumed**) | flats ±0.02, symmetric 0.02 |
| 41.2 | 41.94 | e-clip groove (holds the burr down) | Ø6.0, 0.74 wide (DIN 6799 size 6) | |
| 41.94 | 70.5 | plain | Ø8.0 | ±0.02 |
| 70.5 | 71.24 | e-clip groove (spring seat) | Ø6.0, 0.74 wide | |
| 71.24 | 89.0 | plain | Ø8.0 | ±0.02 |
| 89.0 | 100.0 | top bearing seat (long enough for the 2 mm of travel) | Ø8.000 | **h5**, Ra 0.4 |
| 100.0 | 121.0 | top end | Ø8.0 | ±0.02 |
| 109.0 | 121.0 | crank flat | flat to 7.20 across | ±0.02 |
| 121.0 | | top end | 0.3 chamfer, face flat (the magnet sits on it) | |

Length 121.0. Runout of both bearing seats to each other 0.005; burr drive runout 0.01 to the seats; straightness
0.01 over the length. The shaft slides 2 mm through the top bearing's inner ring as the dial turns, which is why both
seats are h5 (a push fit), not a press.

Mass: about 45 g.

### 5.4 Inner-ring spacer (part 10)

303 stainless, Ø11.5 OD × Ø8.2 ID × 2.0 thick, faces parallel 0.01. It lets the spring press on the top bearing's
inner ring only (a 608's inner ring is about 12 mm across), so the seal is never touched.

### 5.5 Crank hub (part 6)

6061-T6, Ø18 × 19. Its bottom sits 3.0 above the lid at grind 0.

| Feature | Size | Tolerance |
|---|---|---|
| Bore | Ø8.0 with a flat at 7.20, 12.0 deep from the bottom | 8 **H8** (+0.022 / 0); flat +0.03 / +0.01 |
| Magnet pocket | Ø6.0 × 3.0, from 12.0 to 15.0 above the bottom, continuing the bore; the shaft's top end touches the magnet | Ø6 **P7** press fit (or Loctite 638) |
| Arm seat | a 6.0 wide, 3.0 deep slot across the top (floor at 16.0) | width +0.05 / +0.02 |
| Arm screws | 2 × M3 tapped 6 deep from the slot floor, 12 apart (clear of the bore and the magnet) | |

### 5.6 Crank arm (part 5)

6061-T6 plate 6.0, waterjet or milled. Length 100, width 14 at the hub end tapering to 12 at the knob, ends full
radius. Hole centres: hub 0, knob **85.0** (crank radius). Two Ø3.4 holes counterbored for M3 heads at the hub end,
12 apart. M4 tapped through at the knob end for the shoulder screw. Flat 0.05.

### 5.7 Crank knob (part 7)

6061-T6, Ø20 × 30, diamond knurl 0.8 pitch on the grip (knobs are knurled; owner, 2026-11-02). Bore Ø10.000
**H7** × 4.0 deep at each end for the two MF105ZZ flanges, Ø6 through between them. It spins on the ISO 7379 Ø5
shoulder screw.

### 5.8 Lid (part 8)

6061-T6, Ø64.0 × 4.0 plate with a spigot Ø39.90 (**f7**) × 2.0 into the top lip. Centre hole Ø10.0 (clears the
shaft by 1 mm). Crank hub to lid gap: 3.0 at grind 0, 1.0 at grind 119.

### 5.9 Catch cup (part 9)

6061-T6 bar Ø70 × 78, or thick-wall tube.

| Feature | Size | Tolerance |
|---|---|---|
| Outside | Ø68.0 × 74.0 long | |
| Sleeve bore, from the rim | Ø64.20 × 30.0 deep | **H8** (+0.046 / 0) |
| Grounds chamber | Ø60.0 × 40.0 deep (about 110 ml, 30 g of grounds with room to spare) | |
| Base | 4.0 thick, inside corner R2 (easy to empty) | |
| Rim | 1.0 × 30° lead-in, so the O-ring is not cut | |

The cup slides over the dial flange and onto the O-ring at z = 16 (squeeze about 17%), and its internal step stops
against the dial flange. Pushing on the flange cannot turn it, so it cannot change the grind.

### 5.10 Spring (part 13)

Buy to these numbers from any spring catalogue (Lee Spring, Gutekunst, Misumi):

| Property | Value |
|---|---|
| Material | stainless 302/304 |
| Outside | 11.5 to 12.0 max |
| Inside | 8.5 min (clears the Ø8 shaft) |
| Free length | about 20 |
| Installed length | 16.2 at grind 0, 18.2 at grind 119 |
| Rate | 2 to 4 N/mm |
| Force at grind 0 | 12 to 20 N |
| Solid length | under 12 |

Stack from the bottom: e-clip (shaft groove at z_s 70.5), washer 8.4 × 16, spring, spacer, top bearing.

## 6. Where every part sits (for the assembly model)

Tube z, at grind 0. At grind 119 every part on the dial's side of the thread (dial, lower bearing, shaft, inner burr,
e-clips, washer, crank) is 1.98 lower; the tube, bridge, top bearing, spacer, outer burr, lid and plunger do not move.

| Part | z bottom | z top |
|---|---|---|
| Catch cup (base outside) | −50.5 | 23.5 (rim) |
| Grind dial | −6.5 | 28.0 |
| Shaft | 20.0 | 141.0 |
| Lower 608-2RS | 21.0 | 28.0 |
| Shaft collar | 28.0 | 31.0 |
| Outer burr | 30.0 | 50.0 |
| Inner burr | 31.0 | 61.0 |
| Burr e-clip | 61.2 | 61.9 |
| Spring e-clip, washer | 90.5 | 92.8 |
| Spring | 92.8 | 109.0 |
| Spacer | 109.0 | 111.0 |
| Bridge, top 608-2RS | 111.0 | 119.0 (bearing 111.0 to 118.0) |
| Tube | 0 | 122.0 |
| Lid | 120.0 (spigot) | 126.0 |
| Crank hub | 129.0 | 148.0 |
| Crank arm | 145.0 | 151.0 |
| Knob (on the arm, 85.0 off the axis) | 151.5 | 181.5 |

Overall: about 232 mm from the cup's base to the top of the knob, Ø68 at the cup.

## 7. Assembly order

The order matters: the outer burr cannot pass the inner burr once both are in.

1. Press a 608-2RS into the bridge from below, onto its lip.
2. Push the bridge up through the tube's bottom, through the hopper, into its seat against the shoulder. Fit the M4
   × 12 button screw at z 115 into the bridge's groove.
3. Push the outer burr up into its seat against the shoulder. Fit the two M4 × 6 button screws into its notches.
4. On the shaft, from the top end: inner burr down onto the collar, e-clip above it; then e-clip at z_s 70.5, washer,
   spring, spacer.
5. Press the second 608-2RS onto the shaft's bottom seat, against the collar.
6. Push the shaft up from below: its top end goes through the top bearing, the spring compresses a little.
7. Grease the dial thread lightly. Screw the dial in from below; its bearing seat takes the lower bearing. Keep
   turning, clicking, until the burrs just touch when the shaft is turned by hand.
8. That is grind 0. Read the angle of the dial against the tube's index line.
9. On the first build, laser-etch line 0 of the scale at that angle (the scale is etched after this step, on the
   assembled part). On later rebuilds, 0 falls at the same mark because the thread is single-start.
10. Lid on, crank hub over the flat (the magnet holds it), catch cup on.

Cleaning: unscrew the dial, and the shaft and inner burr drop out with it. Nothing else needs to come apart.

## 8. Marking (design language: etched, part names by each wear part)

| Where | What |
|---|---|
| Tube OD at z 4 to 10 | index line at 0°, the product's index (charcoal until grindmn has a hue) |
| Tube OD at z 40 | `48 mm conical` beside the burr screws |
| Tube OD at z 115 | `608-2RS` beside the bridge screw |
| Tube OD at z 22 | `608-2RS` beside the plunger (the lower bearing sits behind it) |
| Tube OD, a band at z 60 to 100 | the mn dot grid, etched (grip and signature; etched, not knurled, since bodies are never knurled) |
| Dial flange chamfer | 60 lines, 0 to 55 numbered |
| Catch cup base | grindmn mark, model version, build date and serial, in Plex Mono; `16.7 µm / click` |

## 9. Numbers to check on the first build

| Check | Target | How |
|---|---|---|
| Inner burr runout at its base | ≤ 0.02 | dial indicator through the bottom with the dial removed and a test bush in its place, or a feeler at four points |
| Axial travel per click | 16.7 µm ± 1 | dial indicator on the shaft's top end over 60 clicks: 1.000 ± 0.02 mm |
| Grind 0 repeat after a strip and rebuild | same mark ± 1 click | |
| Torque to turn the dial | firm, under about 0.5 N·m | |
| Noise | 40 dB(A) at 1 m (the design language's figure, a target to measure) | |
| Mass | about 1 kg with burrs (tube 360, dial 200, cup 160, burrs about 200, rest 60) | scale |

## 10. Assumptions to confirm

| # | Assumption | Why | If it changes |
|---|---|---|---|
| 1 | The burr sizes in section 2 | only the bought burr set can tell | burr seat, hopper, collar, groove positions |
| 2 | Adjustment at the bottom by a threaded dial, shaft held from below | every load goes one way into the thread, one setup for all seats | a top adjuster needs the top bearing pushed down into its seat, which needs a second setup |
| 3 | 1 mm pitch, 60 clicks a turn (16.7 µm) | in the design language's 15–20 µm; a standard ISO fine thread | 48 clicks gives 20.8 µm; 0.75 pitch needs a non-standard M58 × 0.75 |
| 4 | Grind dial in 303 stainless | it slides and turns in bare aluminium; stainless on aluminium does not gall like aluminium on aluminium | a hard-anodised aluminium dial saves about 130 g but the coating must be allowed for in the fits |
| 5 | Ø64 body, one diameter full length | smallest outside that keeps 3 mm of wall at the M58 thread; the hopper wall is 7 mm, so it is heavy (about 1 kg in all) | turn the hopper zone (z 55 to 119) down to Ø58 to save about 90 g, at the cost of a stepped body; grows with D_ob |
| 6 | Catch cup over the tube on an O-ring, not threaded | a thread at the bottom would leave under 1.5 mm of wall | |
| 7 | Crank held by a magnet on a 416 shaft | pulls off without a tool for loading beans | an M4 screw in the shaft end if the magnet is not enough |
| 8 | No hue | grindmn is archived (2026-11-05) | a revival needs a colour decision |
