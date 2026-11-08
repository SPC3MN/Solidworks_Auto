# Backend: FreeCAD 1.x (Python API, headless)

Status: **target, not built.** FreeCAD is not installed on this machine yet (checked 2026-11-08), and none of the
repo scripts run on it. Everything below is an API mapping from FreeCAD's documented Python interface,
**unverified here**. Run the probe at the end, fix this page from what it shows, and move findings to a
`docs/freecad_findings.md` (the counterpart of `docs/solidworks_findings.md`) before relying on any of it.

## Why it fits this workflow

The modules already describe every part as ops with exact volumes. FreeCAD's `Part` module (OpenCASCADE) can
build those ops directly as B-rep booleans, with no GUI, no COM, no focus stealing and no open tabs. So the port is
mostly one file: a `Part`-compatible builder (`scripts/fclib.py`), plus a backend switch in the pipeline and the
assembly check.

## Setup (to verify)

- Install FreeCAD 1.0 or later (it bundles its own Python, 3.11 for 1.0). Ask the user before downloading;
  give the file name, source (freecad.org or its GitHub releases) and size.
- Run scripts headless with `"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" script.py` or with the bundled
  `bin\python.exe`. The repo's `.venv` (Python 3.14) **cannot** import FreeCAD's modules: the Python versions
  must match. Keep pure-Python checks (STL volume, watertightness) importable from both.
- Units: the API works in mm (no metre conversion, unlike SolidWorks).

## Contract mapping (to verify)

| Contract | FreeCAD (Part module) |
|---|---|
| Profiles | `Part.makePolygon([...], True)`, `Part.makeCircle(r, center, normal)`, `Part.Wire(...)`. Nested contours (rings, ports) → `Part.Face(wires, "Part::FaceMakerBullseye")`, which makes holes of inner wires. |
| Planes | Build profiles in local (u, v) and place them: z-plane (x, y) at z0; y-plane (x, z) at y0; x-plane (y, z) at x0, with the matching normal. Keep the module's axis conventions, so op lists port unchanged. |
| `add` / `cut` | `face.extrude(normal * h)` gives the tool solid; `shape = shape.fuse(tool).removeSplitter()` or `shape = shape.cut(tool)`. Fuse all of an op's tools first, then do one boolean. |
| `pattern` | Rotate copies of the seed op's *tool* (`tool.copy().rotate(origin, Z, 360k/n)`), make a compound, one cut. Expect it to be faster than SolidWorks, and the volume must still be (n − 1) × seed. |
| `sweep` | Path wire from lines and arcs (`Part.LineSegment`, `Part.Arc`), circle profile at the start normal to the path, `wire.makePipeShell([profile_wire], True, True)`. |
| `fillet` | `shape.makeFillet(r, edges)`, picking edges by geometry (e.g. edges whose centre is nearest a point), not by screen picks. Likely more reliable than the SolidWorks picks. |
| `shell` | `shape.makeThickness([faces], -t, 1e-3)`. |
| Measure | `len(shape.Solids)`, `shape.BoundBox.XLength/YLength/ZLength`, `shape.Volume`, `shape.isValid()`. |
| Native file | `doc = App.newDocument(name)`; one `Part::Feature` per op or just the result; `doc.saveAs("....FCStd")`; `App.closeDocument(name)`. Parametric links to `params.json` (spreadsheet + PartDesign) are optional; start with plain shapes. |
| STEP | `shape.exportStep(path)`; re-import with `Part.read(path)` and measure again. |
| STL | `MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=0.2)`, then `mesh.write(path)`; the pure-Python STL checks stay as they are. |
| Render | Headless has no 3D view. Options: (a) run FreeCAD with its GUI and use `FreeCADGui.ActiveDocument.ActiveView.saveImage(path, w, h, "White")` after setting a Z-up camera; (b) render the exported STL with Blender in background mode (the `product-render` skill already drives Blender). Decide with the probe. |
| Assembly | Place shapes with `App.Placement(App.Matrix(...))` built from the same `at` / `rot_z` / `xform` rows. Check bbox on the compound; interference pairwise with a bbox prefilter and `a.common(b).Volume > 1e-6` (touching faces give zero volume, like SolidWorks with coincidence off). Save as an `.FCStd` with `App::Link` objects, export the compound to STEP. FreeCAD 1.0's Assembly workbench is optional. |
| Drawings | TechDraw (`TechDraw::DrawPage`, `DrawViewPart`, dimensions). Port the dimensioned-drawing skill only when needed. |

## Expected differences from SolidWorks (to confirm)

- The SolidWorks "sketch line partly overlapping a model edge" rejection should not exist (booleans, no
  sketches). But coplanar or tangent booleans can leave sliver faces; `removeSplitter()` and the 0.05 to 0.6 mm
  offsets still help.
- Cut direction is explicit (the extrude vector), so the "blind cuts go against the normal" rule goes away.
- A self-crossing face still fails (invalid face or zero-volume tool). Check `face.isValid()` before extruding.
- No documents left open in a GUI, but scripts must still close their documents (`App.closeDocument`) and keep
  scratch files in the session scratchpad.

## Probe (first run after install)

Port in this order and stop to fix this page after each step:

1. `fclib.Part` with `add`, `cut`, `pattern`: rebuild `projects/example_box` and the 12-hole pattern probe (tube
   Ø100 / Ø94 × 30, two holes, 12 instances: the removed volume must be 12 × the seed).
2. The pipeline on `example_box` and `example_tray` with `--backend freecad` (or a `CAD_BACKEND` variable): 9/9.
3. A heavy part: `airmn_pleat_pack` (960-line zigzag) and `airmn_fan_housing` (1132 holes). Record build and
   export times against SolidWorks.
4. The airmn assembly: the bbox and the no-interference result must match the SolidWorks run.

Until step 2 passes, build with the SolidWorks backend.
