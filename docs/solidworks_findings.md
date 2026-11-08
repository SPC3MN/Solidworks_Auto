# SolidWorks findings (Windows machine)

Probed on 2026-11-05 with [scripts/sw_probe.py](../scripts/sw_probe.py).

## Environment

- SOLIDWORKS 2025 (revision 33.5.0) is the registered COM server, at
  `C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\`. A 2024 install (32.2.0) also
  exists under `SOLIDWORKS (2)`.
- The default part template still points to the 2023 folder:
  `C:\ProgramData\SolidWorks\SOLIDWORKS 2023\templates\Part.prtdot`. It works.
- Python 3.14 (Microsoft Store build). `pywin32` is installed in `.venv`.
- Not installed: git, uv, Claude Code CLI, PrusaSlicer. `dotnet` is present.

## Verified

- **Test 1 passes.** Attached to a running SolidWorks with `GetActiveObject`,
  built a 100Ã—60Ã—30 mm box (sketch on Front Plane, then `FeatureExtrusion3`) and
  read back a bounding box of 100.0Ã—60.0Ã—30.0 mm and a volume of 180000 mmÂ³.
  Saved as `.SLDPRT`.
- Licence and API automation work (open question 1).
- Python + pywin32 with late binding is good enough as the integration route for
  now (open question 2).

## Parameter binding (open question 4): Global Variables + Equations

Chosen over Design Tables (those need Excel and are harder to edit through the
API). Verified with [scripts/sw_params.py](../scripts/sw_params.py), which reads
`projects/_probe/parameters/params.json`:

- Each parameter becomes a global variable (`"outer_length" = 100mm`), and each
  driving dimension gets a link equation (`"D1@Sketch1" = "outer_length"`).
- The sketch reports `GetConstrainedStatus == 3` (fully constrained) once the
  corner is made coincident with the origin and both sides are dimensioned.
- **Test 2 passes:** changing `outer_length` from 100 to 120 inside the model and
  rebuilding gives a bounding box of 120Ã—60Ã—30.

Gotchas:
- `Dimension.FullName` returns `D1@Sketch1@Part3.Part`. Equations need the
  document suffix removed (`D1@Sketch1`), otherwise they are silently ignored.
- Change a global by writing the `Equation(i)` property in place (a COM
  property-put through `_oleobj_.Invoke`). Calling `Delete(i)` followed by
  `Add2(i, ...)` breaks every equation that references the variable (it then
  evaluates to 0). `SetEquationAndConfigurationOption` returns -1.
- `EquationMgr.EvaluateAll` returns -1 even when it works. `AutomaticRebuild` is
  off, so call `EditRebuild3` afterwards.
- Turn off the `swInputDimValOnCreate` preference (10) while adding dimensions,
  otherwise a modal value box blocks automation. The script restores it at the end.
- `SaveAs3` fails silently if another open document holds the target path. Call
  `CloseDoc(path)` first.

## Example pipeline (tests 1, 2, 6, 7)

[scripts/pipeline.py](../scripts/pipeline.py) runs `projects/<name>/design/model.py`
into `.staging/` and checks the result against `validation/spec.json`: solid body
count, bounding box and volume. It exports STEP and STL, then checks them
independently. The STEP file is reopened in SolidWorks and its volume compared
with the native model. The STL volume and watertightness are computed in pure
Python. A report goes to `validation/history/`, and files are promoted to
`design/` and `exports/` only on a pass.

Results on `projects/example_box`:
- Normal run: 8/8 checks pass, and the files are promoted.
- `--override outer_length=118`: `bbox.x` and `volume` fail. The `bbox.x` failure
  carries `hint.param = outer_length` for autocorrection. Nothing is promoted
  (the hash of the promoted STEP is unchanged).

Notes: `SaveAs3` picks the export format from the file extension. `LoadFile4`
imports STEP without opening a dialog. Body validity (`IBody2.Check`) isn't
checked yet; only the solid body count is.

## Feature library and renders

[scripts/swlib.py](../scripts/swlib.py) is verified on `projects/example_tray`
(extrude with a rounded-rectangle profile, a shell open at the top, and four
through holes). The volume came out at 19070.99 mmÂ³ against 19070.98 by hand,
and all 8 checks pass.

- `InsertFeatureShell` is a method of `ModelDoc2`, not of `FeatureManager`.
- In `FeatureCut4`, `Flip` means "cut outside the profile" and `Dir` reverses the
  direction. Through-all cuts use both directions, so the side doesn't matter.
- Renders: the named views (`*Isometric` etc.) assume Y is up. Our models use Z
  as height, so `render()` sets `ActiveView.Orientation3` from a MathTransform
  whose 3Ã—3 rotation is column-major (screen-right, screen-up, toward-viewer as
  columns). `SaveAs3` to `.png` saves the zoomed view; `SaveBMP` didn't zoom.
- `GetMathUtility.CreateTransform` has to be called through
  `_oleobj_.Invoke(..., DISPATCH_METHOD, ...)` because late binding treats it
  as a property.

## Sideways features (first photo model: projects/rpi_dac_hat)

- Sketches on the Top Plane (normal +Y) map model (x, z) to sketch (x, âˆ’z).
  This was confirmed with bounding boxes. In `FeatureExtrusion3`, the third
  argument (`Dir`) reverses the direction; `down=True` goes toward âˆ’Y.
- **A sketch is rejected when its lines partly overlap existing model edges.**
  Example: an 11 mm wide flange whose top and bottom lines lay on the edges of
  a 10 mm housing. The feature returns `None`. Fix: offset the profile so its
  edges either match an edge exactly or stay clear of it.
- `ViewZoomtofit2`, `GraphicsRedraw2` and `BlankRefGeom` do nothing when accessed
  as properties. Call them with `_invoke` (`DISPATCH_METHOD`). Hide reference
  planes before rendering, or zoom-to-fit frames the planes.

## Package detail (scripts/details.py)

All three board models get leads, end caps, QFN pads and pin-1 dimples, a
lidded SoC, moulded BGAs and real connector openings from one module. Every
detail op carries its exact volume, and the build matched that arithmetic on
all three boards (DAC+ 10889.666 vs 10889.67; DAC Pro 13368.682 vs 13368.68;
Pi 5 18047.383 vs 18047.38).

- **Blind cuts default to going against the plane normal**, the opposite of
  extrudes. A cut toward âˆ’axis therefore needs `Dir = False` (verified with a probe).
- Right Plane sketches map model (y, z) to sketch (âˆ’z, y), and extrudes go toward +X.
- **Select the new sketch explicitly before each feature call.** Otherwise
  `FeatureExtrusion3` sometimes fails or builds from a stale selection. That gave
  6 bodies and a 63.6 mmÂ³ volume deficit before it was fixed.
- A body extruded onto the top faces of lead or pad features merges with them
  (face contact is enough).
- STL export writes the *active* document, so the pipeline activates the model first.
- `ViewZoomTo2` doesn't take model coordinates. For close-ups, select faces and
  call `ViewZoomToSelection` (pick points must land on part tops, not the PCB).
- `CloseAllDocuments` is off-limits (it discards work). Save each document,
  then close it with `CloseDoc`.

## PCB tracks (scripts/tracks.py), generated rather than real

**Removed from all models at the user's request (2026-11-05).** The router,
the `tracks.apply` hooks (which do nothing when a layout has no `tracks` key)
and the pipeline's `features` check remain for future use.

The real copper routing isn't known, so the tracks are generated. A 0.5 mm
grid router runs from each passive end and each IC to the nearest part or
connector, keeping clear of parts, holes, headers and other tracks. Tracks are
0.3 Ã— 0.035 mm, with mitred corners, so each track's volume is exactly length Ã— width Ã— thickness.

- Tracks add only 0.2 to 2.6 mmÂ³ per board, below the 0.1 % total-volume
  tolerance. So the spec has a `features.Tracks` entry: the pipeline
  suppresses the feature, measures the volume it contributed and restores it.
  All 7 boards matched to within 1 %.
- Re-run `scripts/tracks.py` after any layout change. `tpa3255_4ch/design/gen_layout.py`
  regenerates the layout without tracks.

## Assemblies (scripts/assembly.py)

`assemblies/<name>/assembly.json` lists promoted parts with a position in mm
and a rotation about Z. The script builds a `.SLDASM`, fixes every component,
then checks the component count, the bounding box (hand-worked) and interference.
It saves the assembly and a STEP export, renders it, and writes a report to
`validation/history/`.

- `AddComponent5` needs the part already open (`OpenDoc6`). The part's own tab
  can be closed afterwards while the assembly keeps it loaded.
- Placement: `comp.Transform2 = CreateTransform([c, s, 0, -s, c, 0, 0, 0, 1, tx, ty, tz, 1, 0, 0, 0])`,
  translation in metres. Verified with bounding boxes: rot_z âˆ’90 maps local (x, y) to (y, âˆ’x).
- `Select4` and `SaveAs3` need `NOTHING` (`VARIANT(VT_DISPATCH, None)`), not Python `None`.
- `InterferenceDetectionManager` with `TreatCoincidenceAsInterference = False`:
  touching faces don't count. A probe with the HAT lowered to z = 8 reported
  the expected socket, standoff and pin collisions, so a run that finds none is meaningful.
- The HAT model had its far hole line at y = 53 instead of 52.5 (58 Ã— 49 pattern). Fixed with `hole_pitch_y`.
- Wireframe renders are recoloured to off-white lines on charcoal (`recolor()`).
  Grey values of 190 and above are SolidWorks' background gradient and become the flat charcoal background.

## Sweeps (swlib.Part.sweep)

- `InsertProtrusionSwept4` has a built-in circular profile: pass `CircularProfile=True` and
  `CircularProfileDiameter`, then only the path sketch is needed, selected with mark 4.
  Arguments: `(False, False, 0, False, False, 0, 0, False, 0, 0, 0, 0, True, True, True, 0, True, True, d, 0)`.
- The path is built from lines and tangent arcs (`swlib.path`), so its length is exact. The volume is
  πr² × length whenever the bend radius is larger than r, and the cable parts matched it to 0.1 %.
- There's no type info on the live object (`GetTypeInfo` gives "Invalid index"). Read the
  signatures from `sldworks.tlb` with `pythoncom.LoadTypeLib` instead.

## Drawings (scripts/drawing.py)

- The drawing template is user preference 10 (`Drawing.drwdot`). Pass paper size 12 (user-defined) to `NewDocument`, then call `Sheet.SetSize`.
- **The first view auto-scales the sheet** (it went to 10:1). Call `Sheet.SetScale(1, 1, False, False)`
  after placing the views, otherwise the sheet sketch and notes come out 10× too big.
- `CreateDrawViewFromModelView3(path, "Z_front", x, y, 0)` uses named views saved in the part
  (`Orientation3`, then `NameView`), so the drawing views are Z-up.
  Set each view's scale with `UseSheetScale = False` and `ScaleDecimal`.
- To sketch the border on the sheet, call `_invoke(doc, "EditSheet")` and `ActivateSheet` first.
  Without them the lines go into the last view's sketch.
- `MathUtility.CreatePoint` and `MathPoint.MultiplyTransform` need `_invoke`, and their raw
  results need `win32com.client.Dispatch`. `View.ModelToViewTransform` maps model metres to sheet metres.
- `SelectByID2("", "EDGE", sx, sy, ...)` on a drawing picks the nearest edge.
  - Then use `AddDimension2`, `AddHorizontalDimension2` or `AddVerticalDimension2`.
  - Read the result back with `GetDimension2(0).SystemValue` (in metres).
  - `GetSystemValue3` returns None here.
- Circles seen edge-on can't be selected (the type falls back to 12, the drawing view itself).
- PNG export of a drawing is screen resolution; call `ViewZoomtofit2` first. The PDF is vector.

## Port interiors and a stalled build (2026-11-06)

- Port openings are cut as `("ring", outer, tongue)` profiles: two nested contours in one sketch.
  SolidWorks cuts the region between them and leaves the tongue joined to the back of the pocket.
  Volumes match the arithmetic exactly. The Pi 5 went from 18047.38 to 19073.86 mm³.
- The Zero 2 W build stalled once for more than 15 minutes, with SolidWorks "Not Responding" and
  using about 2 cores. Killing the Python script does not interrupt SolidWorks. SolidWorks had been
  running for about 16 hours across many builds. After a force-close and restart, the same build
  passed in under a minute, so the stall was in the session, not the geometry. If a build takes
  more than about 5 minutes, restart SolidWorks (asking the user first) before debugging the model.

## pywin32 late-binding quirks

- Methods with no arguments show up as properties: use `app.RevisionNumber` and
  `ext.CreateMassProperty`, without `()`.
- Pass a null COM object as `VARIANT(VT_DISPATCH, None)`. Pass out-parameters as
  `VARIANT(VT_BYREF | VT_I4, 0)`.
- The API uses metres.

## Still open

Questions 3, 5, 6 and 7 in [solidworks_open_questions.md](solidworks_open_questions.md):
modal dialogs in general, export settings, geometry queries, and the missing
tools above. Not yet done: syncing edits made in the GUI back into `params.json`.
Every script run leaves its part open in SolidWorks (Part1, Part2 and so on).

## Drawing picks on large sheets (SSR-RACK48, 2026-11-06)

`SelectByID2` on a drawing uses a screen-pixel tolerance. With a whole A2 sheet in the window, a Ø3.5 hole at 1:2 was about 1.5 px wide, so picks on it chose the board edge 3 mm away. The result was wrong values or angles (1570.8 = 90°). `drawing.py` now calls `ViewZoomTo2` on a ±8 mm box of the sheet, which works in sheet coordinates for drawings, before each pick, and `ViewZoomtofit2` before saving.

## Rounded tops on small cylinders (SSR-RACK48 LED domes, 2026-11-06)

- Fillet edges picked by points on 48 Ø3 circle edges: only 12 were rounded, whether the pick was at 0° or 45°.
- Picking each flat top face at its centre and filleting the faces: 46 of 48 were rounded. Looking down −Z first didn't change that. The 2 misses (SSR7) have no obvious cause.
- `board_build` now checks each top face's area after the fillet and rounds any still at full size in a `_fix` feature. The pipeline's feature check takes a prefix (`RoundTop*`) and suppresses those features together. That result was exact: −98.229 mm³.
- The total-volume check can't see this. The rounds are 0.01 % of the volume, under the 0.1 % tolerance, and the first build passed all 9 checks with no rounds at all. Small features need a `features` check.

## Section views in drawings (grindmn, 2026-11-06)

- `drawing.py` `"section": true` replaces the front view with section A-A, cut along x through the origin in the top view.
- The cut line must be drawn in the top view's own sketch (`ActivateView`, then `CreateLine` in view coordinates, model metres) and selected with `Select4`. Drawn in sheet coordinates it does not cut: the "section" is just the flipped outside view.
- Drawn from +x to -x the section is z-up, x-right. Drawn from -x to +x it comes out upside down.
- `CreateLine` sometimes throws "The server threw an exception" for one length (grindmn_lid at 74 mm) and works for a slightly longer one; `drawing.py` retries longer lengths.
- Section-face boundaries are ordinary lines, so bore diameters (width between the two walls) and axial steps pick reliably. Width dimensions on a turned section get the diameter sign automatically.
- `DisplayDimension.SetText`: 1 = prefix, 2 = suffix, 3 = callout above. A prefix replaces the automatic diameter sign.
- Circles interrupted by spokes are arcs: a single pick gives the radius (R), not the diameter.

## Simplifying existing assemblies (Stereo_Rig_V2, TANK, 2026-11-06)

Tools: `scripts/asm_capture.py` -> `scripts/asm_simplify.py gen` -> `pipeline.py` on each
`projects/x8020_*` -> `scripts/frame_check.py` -> `asm_simplify.py assemble` -> `assembly.py`.
The source-to-simple mapping lives in `assemblies/x8020_map.json`, and the solved frames in `assemblies/x8020_frames.json`.

- `Component2.Transform2` is **relative to the root assembly** for components at any depth, including
  inside virtual sub-assemblies. Transformed part boxes matched `GetBox` to within 0.001 mm on all 433 leaves.
- Late binding exposes `IsSuppressed`, `GetFaceCount`, `IsCylinder` and `GetVertices` as methods on some objects
  and as properties on others. Check `callable()` before calling.
- Vendor parts use their own frames: 80/20 rails are centred on the origin along Z, Faztek rails run from 0 to L with an
  offset section, and gussets differ by vendor. Each simplified part therefore gets a per-source local transform. Profiles
  are solved from the bbox; brackets and fasteners from the 24 axis rotations, choosing the one with the best
  interference overlap against the original. The best candidate was always clearly ahead.
- Watch for mitred rails. The 1530 brace has 60° and 30° end cuts, and the Faztek `5 - V3` has a 45° cut. Square-ended rails
  then poke into their neighbours: the interference check found it at 70 591 mm³. Measure the end vertices and use `miters`.
- Function check: run interference detection on the original (the baseline, about 20 s each) and allow only pairs that
  are not new. The noise floor is about 20 mm³ of fit difference. Bolts reaching into a slot without a T-cavity are expected.
- The source assemblies differ in up axis: TANK is Y-up and the rig is Z-up (`source_up` in the map).
- Results: rig 12 216 -> 1 337 faces (9.1x); TANK 6 618 -> 4 394 (most of its parts were already simple, so they were kept).
  Building assemblies of 112 and 321 components takes several minutes, so run them in the background.

## Circular patterns and heavy parts (airmn, 2026-11-08)

- `Part.circular_pattern(name, features, n)`: creates `Axis_Z` once with `InsertAxis2(True)` after selecting
  Top Plane and Right Plane (their intersection is model Z here), selects it with mark 1 and the seed features
  (`BODYFEATURE`) with mark 4, then calls `FeatureCircularPattern4(n, 2*pi, False, "NULL", True, True, False)`
  (geometry pattern, equal spacing). A 12-instance probe removed exactly 12 × the seed volume, and the 133-unit
  dot-grid band (2128 holes) matched the hand integral.
- A part with thousands of holes is quick to build but slow to export: the 2512-hole band wrote a 63 MB STEP,
  and the pipeline's STEP re-import took about 10 minutes. 1969 holes cut from one flat sketch was fine.
- A zigzag polygon of 960 lines per contour (the pleat pack and comb) builds in under a minute. A mitred offset
  outline that crosses itself makes `FeatureCut4` return None with no other error.
- SolidWorks dropped its COM connection once during a batch ("The object invoked has disconnected from its
  clients"). It came back on its own (a new process), and every later call in that run failed until the
  script was restarted.
- `app.GetFirstDocument` and `doc.GetNext` are properties under late binding. Calling them with `()` raises
  "Member not found".
