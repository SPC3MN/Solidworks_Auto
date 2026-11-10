# Backend: FreeCAD 1.x (Python API, headless)

Status: **part backend built and verified** on FreeCAD 1.1.4 (Linux Flatpak), 2026-11-08:
`scripts/fc/fclib.py` (swlib's API on OCCT booleans), `scripts/fc/fc_job.py` (runs in FreeCADCmd) and
`pipeline.py --backend freecad`. Verified behaviour is in [docs/freecad_findings.md](../../../../docs/freecad_findings.md);
it overrides the mapping below where they differ. Assemblies: `python3 scripts/assembly.py assemblies/<name>
--backend freecad` (`scripts/fc/fc_assembly.py`) places each part's promoted STEP and checks component count, bbox
and pairwise interference against `assembly.json`. FreeCAD-only kernel ops (revolve, loft, tilted planes, helix,
chamfer, edge selection, section checks) are in the next section. Not built yet: TechDraw drawings, GUI-parametric `.FCStd` files
(the native file holds the result shape plus a `Params` spreadsheet), and the vendor-assembly options
(`baseline_interference`, `faces_before`, explode lines).

Run: `python3 scripts/pipeline.py projects/<name> --backend freecad` (the default off Windows; `CAD_BACKEND`
overrides it). Add `--no-promote` to check without copying outputs into `design/` and `exports/`.

## Ops beyond swlib (FreeCAD only, verified 2026-11-09)

New parts `import fclib` directly. Each op has a probe project (`projects/example_*`) and a hand formula in
`scripts/handcalc.py`; `docs/freecad_findings.md` has the details.

| Op | Call | Hand value |
|---|---|---|
| Turn a profile | `part.revolve(name, profiles, about="z", angle=360, at=(0, 0, 0), cut=False)`; profile in (x, z) for about z, (x, y) for about x or y | `handcalc.revolve_volume(points, angle)` |
| Sketch on any plane | `p = fclib.plane("z", origin=(x, y, z)).rotated("y", 30)`, then `extrude(..., plane=p)` / `cut(..., plane=p)`; profile coordinates are measured from the origin | `handcalc.tilted_hole(d, t, angle)`; an oblique boss holds area × axial length |
| Loft | `part.loft(name, [(profile, z), ...], ruled=False, cut=False, axis="z")`; a section may also be `(profile, Plane)` | ruled: `handcalc.prismatoid`, `handcalc.frustum`; smooth: none, use sections |
| Spring / coil | `part.helix(name, d, radius, pitch, height, z=0, left=False)` | `handcalc.helix_volume` |
| Chamfer | `part.chamfer(name, size, edge_points)` or `select=` | `handcalc.chamfer_edge`, `chamfer_rim` |
| Pick edges by geometry | `select=fclib.edges(parallel="z", on=("z", 10), radius=5, box=(lo, hi))` on `fillet` and `chamfer`; all given tests must hold | `handcalc.fillet_edge`, `fillet_rim` |

Rules that came out of the probes:

- Run cut profiles 1 mm past the surface they open and count the volume only inside.
- A turned part is one `revolve` of its half-section; grooves and bores are revolve cuts. This replaces "extrude
  the solid, then cut every bore" on this backend.
- **Freeform parts** (a smooth loft, anything without a closed-form volume): leave `volume` out of `spec.json` and
  give `"sections": {"waist": {"axis": "z", "at": 30, "size": [24, 24], "tol": 0.05, "area": 168.861}}`. `size` is
  the cross-section's extent on the plane's two axes, `area` is optional. Put a station at every section the loft
  was built from and wherever else a size matters; between stations nothing is known by hand. Keep the bbox check.
- Hollow a lofted body with a second loft as a cut (`cut=True`) through stations the wall thickness smaller;
  `shell` fails on ruled lofts with kinks.
- `features` volumes are signed (a cut is negative) and only valid for features no later selector depends on.
- A thin round wire meshes under its volume; give `export.stl` 2 % for springs.

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
