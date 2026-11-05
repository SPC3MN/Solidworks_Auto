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
  built a 100×60×30 mm box (sketch on Front Plane, then `FeatureExtrusion3`) and
  read back a bounding box of 100.0×60.0×30.0 mm and a volume of 180000 mm³.
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
  rebuilding gives a bounding box of 120×60×30.

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
through holes). The volume came out at 19070.99 mm³ against 19070.98 by hand,
and all 8 checks pass.

- `InsertFeatureShell` is a method of `ModelDoc2`, not of `FeatureManager`.
- In `FeatureCut4`, `Flip` means "cut outside the profile" and `Dir` reverses the
  direction. Through-all cuts use both directions, so the side doesn't matter.
- Renders: the named views (`*Isometric` etc.) assume Y is up. Our models use Z
  as height, so `render()` sets `ActiveView.Orientation3` from a MathTransform
  whose 3×3 rotation is column-major (screen-right, screen-up, toward-viewer as
  columns). `SaveAs3` to `.png` saves the zoomed view; `SaveBMP` didn't zoom.
- `GetMathUtility.CreateTransform` has to be called through
  `_oleobj_.Invoke(..., DISPATCH_METHOD, ...)` because late binding treats it
  as a property.

## Sideways features (first photo model: projects/rpi_dac_hat)

- Sketches on the Top Plane (normal +Y) map model (x, z) to sketch (x, −z).
  This was confirmed with bounding boxes. In `FeatureExtrusion3`, the third
  argument (`Dir`) reverses the direction; `down=True` goes toward −Y.
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
  extrudes. A cut toward −axis therefore needs `Dir = False` (verified with a probe).
- Right Plane sketches map model (y, z) to sketch (−z, y), and extrudes go toward +X.
- **Select the new sketch explicitly before each feature call.** Otherwise
  `FeatureExtrusion3` sometimes fails or builds from a stale selection. That gave
  6 bodies and a 63.6 mm³ volume deficit before it was fixed.
- A body extruded onto the top faces of lead or pad features merges with them
  (face contact is enough).
- STL export writes the *active* document, so the pipeline activates the model first.
- `ViewZoomTo2` doesn't take model coordinates. For close-ups, select faces and
  call `ViewZoomToSelection` (pick points must land on part tops, not the PCB).
- `CloseAllDocuments` is off-limits (it discards work). Save each document,
  then close it with `CloseDoc`.

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
