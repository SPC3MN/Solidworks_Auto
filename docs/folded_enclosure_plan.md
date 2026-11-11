# Plan: hand-folded aluminium enclosures

Source: `aluminum_folding_architecture.txt` (the owner's spec, uploaded to `main` on 2026-11-11). Planned with the
owner the same day in two rounds of questions. Decisions marked **(owner)** were chosen by the owner; the rest
follow from them or from the spec and can be changed.

**Status (2026-11-11): release 1 is built** (section 11), proven on `projects/example_folded_tray` and on a
throwaway `/design` product. No sheet has been cut: every fold is still untested, and no enclosure of the owner's
has been through it.

## 1. Goal

Design an aluminium enclosure as flat sheet that is cut, then folded by hand along weakened lines, and get from a
definition to a flat-pattern DXF, a folded 3D model and a validation report. Two fold methods: laser-cut
perforations that leave bridges, and CNC-machined partial-depth grooves.

The spec's main rule, kept as the centre of the design: **the enclosure, the fold definition and the manufacturing
method are three separate things.** A fold can change from perforated to grooved without touching the panels.

| Decision | Choice |
|---|---|
| Architecture **(owner)** | script-first now, live FreeCAD objects later: plain Python modules driven by a definition file, with the geometry generators free of FreeCAD so a layer of live objects can be added without rewriting them |
| Entry point **(owner)** | a process inside `/design` (brief, board, approval as now), and also runnable on its own from a definition file |
| Constructions, first release **(owner)** | open tray, walls with fastening flanges, and any connected panels (a general panel tree, with templates on top) |
| Panel shapes **(owner)** | polygons with straight fold edges; a fold runs along all or part of one edge |
| Fabrication route **(owner)** | not decided: a generic manufacturing profile with conservative placeholders, marked untested |
| Test coupons **(owner)** | a coupon-sheet generator in the first release |
| Untested folds **(owner)** | allowed, but everything exported is marked UNTESTED; the three validation levels are always reported separately |
| Proving case **(owner)** | an example tray with flanges first, then a real enclosure of the owner's through `/design` |
| Baseline material (spec) | 1.0 mm 5052-H32, experimental; no fold geometry is assumed safe |
| Fold life (spec) | one-time forming, not a hinge |

## 2. The three layers

```
enclosure            panels (polygons, holes, cutouts) joined in a tree by folds
   │
fold definition      which two edges, the span along them, angle, direction, sequence, recipe name
   │
fold recipe          method + its numbers: slots / staggered / multi-row / curved  |  V / round / flat groove
   │                 gives: the pattern on its DXF layer, the hinge position, the flat allowance, its own rules
profiles             material (alloy, temper, thickness, grain, tested recipes)   manufacturing (kerf, minimums, tools)
```

- A **panel** knows nothing about how its edges fold.
- A **fold** names a recipe; it holds no slot or groove numbers.
- A **recipe** is the only place a manufacturing method appears. It supplies three things the layers above need:
  the geometry to cut or machine, where the rigid hinge sits through the thickness (a perforated fold bends at
  its bridges, a grooved one at its remaining web), and the **flat allowance**: how much flat length the fold
  takes up. The allowance is **0 until a coupon has measured it** (the spec: conventional bend arithmetic is not
  to be trusted here).
- Changing a fold's recipe regenerates the flat pattern and the preview; panels and folds are untouched.

### The fold zone

```
        panel A                      panel B
  ──────────────────┐  fold zone  ┌──────────────────
                    │▯▯▯▯ ▯▯▯▯ ▯▯▯▯│        ▯ slot     gap between slots = bridge
  ──────────────────┘◄─allowance─►└──────────────────
                 end clearance at each end of the fold; corner relief where two folds meet
```

## 3. Definition file

One `sheet.json` per sheet-metal part (an enclosure of two sheets is two parts). Sizes are expressions of the
part's parameters, as in `/design` options.

| Block | Holds |
|---|---|
| `material`, `manufacturing` | names of profiles in `libraries/sheet/` |
| `dims` | `outside` or `inside`: what the enclosure's stated sizes mean |
| `panels` | id, outline polygon in the panel's own 2D frame, features (round hole, slot, rectangle, polygon cutout), which face is the inside |
| `folds` | id, parent panel and edge, child panel and edge, span along the edge, angle, direction, sequence number, recipe name |
| `recipes` | name → method and its numbers (slot length, width, bridge, rows, stagger, end clearance; later groove width, depth, angle, radius, web) |
| `hardware` | fasteners for the flanges, for the BOM |

Templates write this file from a few numbers: `tray` (base + 4 walls), `tray` with return flanges, and later the
U-shell and cover. Anything a template cannot express is written as panels and folds directly.

## 4. What is generated

| Output | How |
|---|---|
| Flat pattern | unfold the panel tree: the root panel at the origin, each child laid against its parent's edge with the fold zone between them; the outline is the union of panels and fold zones, less corner reliefs |
| DXF | layers as in the spec: `CUT_THROUGH`, `FOLD_PERFORATION`, `CNC_GROOVE`, `ENGRAVING`, `REFERENCE`, `FOLD_DIRECTION`; mm; laser and CNC geometry never share a layer. Written by a small standard-library writer and read back to check it. |
| Folded model | each panel extruded to the sheet thickness and turned about its fold's hinge axis, down the tree (rigid panels, as the spec allows); STEP export |
| Folding sequence | the same model with folds applied in sequence order, one image per step; exploded view |
| `.FCStd` | generated, laid out in the spec's tree: Parameters, Material Profiles, Manufacturing Profiles, Panels, Folds, Flat Pattern, Folded Preview, Validation, Export |
| Report | the three validation levels, separately (section 5) |

Marked UNTESTED when any fold's recipe has no passing test in the material profile: in the report, in the DXF
(`REFERENCE` layer) and in the file name **(owner)**.

## 5. Validation: three separate verdicts

| Level | Checks | Source of the limits |
|---|---|---|
| **Geometrically valid** | panels form one tree; mating edges and spans agree; the flat pattern does not overlap itself; holes and cutouts lie inside their panel and clear of fold zones; folded panels do not interfere; the fold sequence can be carried out (each fold swept in steps with the earlier ones in place) | geometry only |
| **Manufacturable** | slot width, bridge width, slot-end clearance, spacing between features, corner relief, minimum remaining material, and later groove tool access, each against a minimum | the manufacturing profile (placeholders until a route is chosen) |
| **Experimentally validated** | every fold's recipe matches a tested entry in the material profile: same alloy, temper and thickness, numbers within the tested band, angle no larger than tested, grain direction as tested | coupon results |

A design is never reported as simply "valid". The report states each level, and which folds hold it back.

## 6. Coupons **(owner: first release)**

- `coupons` writes a coupon sheet: strips with one fold each, sweeping slot length, bridge width and row count
  around a starting recipe, each engraved with an ID and with marks for measuring the leg lengths after folding.
  A table lists what each ID is.
- The owner cuts and folds them and records, per ID: held or cracked, the angle reached, the measured legs.
- `record` writes the results into the material profile. Passing recipes become the validated entries of
  section 5, and the measured legs give each recipe its flat allowance.
- The engraved IDs use a small built-in stroke font, since cutting services often drop DXF text.

## 7. Inside `/design` **(owner)**

- A part in a draft may have `"process": "fold"` and point at a sheet definition. Its folded panels are turned
  into the draft's bodies automatically, so the board's section, scorecard, fit checks and massing work unchanged.
- The board also shows the part's flat pattern, with the fold lines and their recipes, and the UNTESTED mark.
- The approval gate covers the sheet definition like any other part. After approval the detail stage runs the
  folding pipeline for that part and the assembly check uses its folded STEP.
- One fold counts as one setup on the simplicity scorecard, and fasteners in flanges count as fasteners.

## 8. Code layout

| File | Role | Runs in |
|---|---|---|
| `scripts/sheet_lib.py` | the model: panels, folds, recipes, profiles; unfolding arithmetic; the validation rules | host Python |
| `scripts/fold_patterns.py` | recipe generators: pure 2D geometry in, 2D geometry out | host Python (no FreeCAD, so live objects can reuse them later) |
| `scripts/dxf_io.py` | layered DXF writer and a reader for the read-back check | host Python |
| `scripts/fc/fc_sheet.py` | outline union, folded solids, interference and sequence sweeps, STEP, the `.FCStd` tree | FreeCADCmd |
| `scripts/sheet_cli.py` | `template`, `flat`, `fold`, `check`, `coupons`, `record`, `export` | host Python |
| `libraries/sheet/materials.json`, `manufacturing.json` | profiles; `5052-H32 1.0 mm` and a generic, untested manufacturing profile to start | data |
| `tests/test_sheet_unit.py`, `tests/test_sheet_fc.py` | unfolding, patterns, DXF round trip, validation; folded model against hand values | |

## 9. Releases

The spec's order, with two changes: coupons move into the first release **(owner)**, and a minimal material
profile comes with them, because coupon results need somewhere to live.

**Release 1**

1. Panel tree, polygons, features; the `tray` template with and without flanges.
2. Fold definitions and recipes as separate objects.
3. Straight interrupted-slot generator: slot length, width, bridge, end clearance.
4. Flat pattern and the layered DXF, with read-back.
5. Folded model, sequence images, interference.
6. Validation at the three levels (geometric in full; manufacturable against the generic profile).
7. Coupon sheet and `record`; the baseline material profile.
8. The `fold` process in `/design`.
9. Proof: an example tray with flanges end to end, then an enclosure of the owner's through `/design`.

**Release 2**: staggered and multi-row slots, curved slits, CNC grooves (V, rounded, flat bottom) on their own
layer, hybrid folds (experimental), fuller material profiles, the U-shell and cover template.

**Release 3**: CAM (FreeCAD Path or a compatible route), tool-access and other manufacturing checks, PDF
manufacturing drawings (needs the TechDraw port in `docs/design_skill_plan.md`), assembly instructions, design
rules drawn from the recorded tests, and the live FreeCAD object layer.

## 10. Still open

- **Where the sheets are cut.** Until that is known, kerf, minimum slot and minimum bridge are placeholders and
  the "manufacturable" verdict means only "passes the placeholders".
- **A starting recipe for 1.0 mm 5052-H32.** The first coupon sweep needs a centre value for slot length and
  bridge width; it will be a labelled guess unless the owner has numbers from a previous build.
- **Corners.** Open corners with a relief notch are assumed. Whether flanges overlap the neighbouring wall inside
  or outside, and which fastener, is decided per enclosure.
- **Order against the rest of the plan.** `docs/design_skill_plan.md` still has the interface-and-hole check,
  the migration and the TechDraw drawings to build. Release 1 here can go before them; only its PDF drawings
  depend on one of them.

## 11. Release 1 as built

Files: `scripts/sheet_lib.py`, `fold_patterns.py`, `dxf_io.py`, `sheet_draw.py`, `sheet_cli.py`, `fc/fc_sheet.py`,
`libraries/sheet/materials.json` and `manufacturing.json`, `tests/test_sheet_unit.py` (12 tests),
`.claude/skills/design/references/folded-sheet.md`. `draft_lib.py`, `design_board.py` and `design_cli.py` carry the
`fold` process.

Proof: `projects/example_folded_tray` (120 × 80 × 30 outside, four walls, four flanges with M3 holes, 8 folds).
Blank 197 × 157; it folds to exactly 120 × 80 × 30; no collisions in the finished part or at any of the 8 sweep
steps; the DXF is one closed outline of 36 points plus 8 holes, 66 slots, and reads back as written. Its verdicts:
geometrically valid yes, manufacturable yes (against placeholder limits), experimentally validated no. A first
coupon sheet is in `coupons/first_sweep/` (9 strips: slots 4, 8, 12 by bridges 1, 1.5, 2).

Differences from the sections above:

| Plan | As built | Why |
|---|---|---|
| commands `flat`, `fold`, `check`, `export` | `check` (host only) and one `build` that does the rest | the outputs come from one FreeCAD run |
| a coupon's measured legs give the recipe its flat allowance | they give the **hinge height**: with rigid panels the two outside legs add up to the flat length plus twice the hinge height, so `record` stores `hinge_measured`; `allowance` stays a separate recipe number | that is what the measurement determines |
| coupon IDs in a stroke font | two-digit numbers in seven-segment strokes; the font also has the letters of UNTESTED | enough for 99 coupons |
| UNTESTED in the DXF | stroke text on the `REFERENCE` layer below the blank, and `_UNTESTED` in the file name | |
| exploded view | not built | left for release 2 |
| the gate covers the sheet definition | the approval hashes the sheet file; at the detail stage the gate compares shared parameters, panels and folds, and lets the recipe change | the spec's rule: the method can change without redesigning the enclosure |
| not planned | walls stop short of each corner by the thickness the neighbouring wall takes up, plus a clearance | with a mid-thickness hinge, full-length walls collide at the corners; the interference check showed it |

Findings:

- Flat faces that share only an edge do not merge reliably in OCCT (`fuse` + `removeSplitter` left 8 pieces). Fusing
  the panels as 1 mm slabs, refining, and taking the bottom face gives one outline.
- The outline's arcs (corner reliefs) are written as polyline bulges, worked out from each arc's mid point.
- The job for FreeCAD goes in a file, not an environment variable, so a large enclosure cannot overflow it.
