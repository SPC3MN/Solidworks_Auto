# FreeCAD findings (verified)

The counterpart of [solidworks_findings.md](solidworks_findings.md): behaviour proven on a real
FreeCAD, not taken from the docs. Machine: Linux Mint 22.3, FreeCAD 1.1.4 (Flatpak
`org.freecad.FreeCAD`), Blender 5.2.3 LTS (portable, `~/Tools`), 2026-11-08.

## Running FreeCAD headless

- `scripts/freecad_run.py` finds FreeCAD (`FREECAD_CMD`, `config/render.local.json` `"freecad"`, install
  folders, PATH, then the Flatpak) and runs a script in `FreeCADCmd`. `"freecad": "flatpak"` selects the
  Flatpak explicitly.
- The Flatpak build is started with `flatpak run --command=FreeCADCmd org.freecad.FreeCAD script.py`. Startup is
  about 1.5 s warm; the first run after boot took about 10 s.
- The Flatpak sandbox shares the host file system **except `/tmp`**, and it does **not** inherit the host
  environment. `freecad_run.run` adds `--filesystem=/tmp` and `--env=NAME=<json>`, so job files in `/tmp` and
  the JSON argument both reach the script.
- FreeCADCmd treats extra command-line words as files to open, so arguments go in one environment variable as
  JSON (`FC_JOB`, `RENDER_FC_ARGS`).
- FreeCAD 1.1.4 bundles **Python 3.13** (the plan assumed 3.11). Nothing imports across interpreters, so it
  doesn't matter, but scripts that run inside FreeCAD must not depend on the host's packages.

## Part backend (scripts/fc/fclib.py)

- The swlib method set on Part-module (OCCT) booleans: profile → `Part.makeFace(wires,
  "Part::FaceMakerBullseye")` (nested wires become holes; separate wires separate faces) → `face.extrude(n * h)`
  → `fuse` / `cut` → `removeSplitter()`.
- `fc_job.py` puts `fclib` in `sys.modules["swlib"]` and `fc_params` in `sys.modules["sw_params"]` before loading
  `model.py`, so model scripts and the shared generators run **unchanged**. Profiles keep swlib's design (a
  callable that draws into a sketch object), so closures such as `details.ring` work as they are.
- Plane families need no sign tables: points are placed directly in 3D, (x, y) at z, (x, z) at y, (y, z) at x.
  Extrudes go toward +axis and blind cuts toward −axis, matching swlib's verified behaviour; through-all cuts
  span the part's bbox diagonal both ways.
- Shell: `shape.makeThickness(faces, -t, 1e-3)` (negative = inward, like SolidWorks). example_tray matches its
  hand-computed volume to 0.007 mm³ (19070.987 vs 19070.98).
- Feature volumes (spec `"features"`) are measured by replaying the op list without the feature, the counterpart
  of suppressing it. Fillet and shell picks are by nearest point and are repeated on every replay.
- STEP from `shape.exportStep` re-reads with `Part.read` at the same volume. STL from
  `MeshPart.meshFromShape(LinearDeflection=0.05, AngularDeflection=0.2)` is binary, watertight, and within 0.02 %
  on the tray (19068.4 vs 19071.0).
- Shell with no open faces (a closed hollow case, `panel_parts`): `makeThickness` rejects an empty face list,
  so the inward offset (`makeOffsetShape(-t, 1e-3, join=2)`) is cut out instead.
- Measure with `shape.optimalBoundingBox(True, False)`. `BoundBox` is loose around curved faces (an O-ring came
  out 69.05 instead of 64.9; screws and swept cables were 2–8 % over) while the volume was right.
- Point picks resolve in 3D (nearest face/edge), so `board_build.py`'s SolidWorks workarounds (look down −Z
  before picking, re-round domes whose pick missed) are skipped on this backend.
- The native `.FCStd` holds the result as one `Part::Feature` plus a `Params` spreadsheet. It is **not**
  parametric in the GUI yet: a parameter change needs a rerun of `model.py` (as for most swlib features).

## Kernel beyond swlib (2026-11-09)

`fclib` now has ops SolidWorks' `swlib` never had: `plane().rotated()`, `Part.revolve`, `Part.loft`, `Part.helix`,
`Part.chamfer` and the `edges()` selector. Each was probed in OCCT first, then built into a probe project that
passes the pipeline against a hand value, and `tests/test_kernel.py` repeats 30 comparisons in one FreeCAD start.
`scripts/handcalc.py` holds the closed-form volumes; every one matched FreeCAD to 6 significant figures or better.

| Op | Probe project | Hand value | FreeCAD |
|---|---|---|---|
| `revolve` (body, V-groove cut, bore cut) | `example_revolve` | 3204 π = 10 065.663 | 10 065.663 |
| tilted `plane` (30° hole, 20° boss) | `example_tilted` | 47 781.646 | 47 781.646 |
| ruled `loft` (hopper, hollowed by a loft cut) | `example_loft` | 11 520.000 | 11 520.000 |
| smooth `loft` (vase through 4 circles) | `example_vase` | none: sections Ø24 and Ø36 | 24.000, 36.000 |
| `fillet` / `chamfer` by `edges()` | `example_edges` | 11 066.910 | 11 066.910 |
| `helix` (spring) | `example_spring` | 988.958 | 988.960 |

- **Revolve.** `face.revolve(point, axis, angle)` returns a Solid directly, also when the profile touches the axis
  and for partial angles; volume is Pappus exactly (arc profiles too: a quarter disc gave a hemisphere to 7 figures).
  A profile that crosses the axis is refused in `fclib` before OCCT sees it.
- **Cut profiles should run past the surface they open** (the groove and bore run 1 mm out), so no cut face lies on
  a body face; the volume is still counted only inside. A loft cut whose end faces were flush with the body's end
  faces (the hopper) also worked.
- **Tilted planes.** A `Plane` is an origin, two in-plane unit vectors and a normal; `plane(axis, origin=...)` keeps
  the usual profile coordinates but measures them from the origin, and `.rotated(about, angle, through=)` pivots
  it. A hole through a plate at angle θ removes π r² t / cos θ while both mouths stay on the faces; a boss cut
  obliquely by the face holds π r² × its axial length above the face. Both exact.
- **Ruled loft** (`OCC.makeLoft(wires, True, True)`) between two parallel sections is a prismatoid:
  h/6 (A₀ + 4 A_mid + A₁), exact for rectangles and for circles (a frustum). Three ruled sections are two stacked
  prismatoids. A twisted pair of squares and a rectangle-to-circle loft are valid solids but have no simple hand volume.
- **Smooth loft** (`ruled=False`) passes through every section exactly (Ø24.000 and Ø36.000 at the vase's
  stations) but between stations its size is the spline's: the vase measured Ø37.52 at z = 1.5 where a straight
  line between the neighbouring sections gives Ø39.2. So a freeform part has **no hand volume and no hand size
  between stations**: its spec drops `volume` and checks `sections` at the stations, and the bbox check is what
  shows the skin does not bulge past the largest section. Put a station wherever a size matters.
- **Shelling a loft.** `Part.shell` (`makeThickness`) with the top face open worked on the smooth four-circle loft
  (one valid solid, 58 729 → 20 031 mm³ at a 2.5 wall) and failed on the same circles lofted ruled, where the skin
  has kinks (`BRep_API: command not done`). Hollowing with a second loft used as a cut worked in both cases and
  keeps the wall checkable at the stations, so the probe parts do that.
- **Sections.** `shape.slice(normal, offset)` returns the section's wires; `FaceMakerBullseye` turns them into a
  face with holes, whose area and optimal bounding box are what `spec.json` `"sections"` checks.
- **Edge selection.** A cylinder's seam is a `GeomLine` edge parallel to the axis with only one ancestor face;
  `edges()` drops every edge with fewer than two faces, otherwise `parallel="z"` would hand the seam to
  `makeFillet`. After a fillet on a box's vertical edges the top rim is 8 edges (4 lines, 4 arcs) and
  `edges(on=("z", H))` chamfers all of them in one go.
- **Fillet and chamfer volumes.** Straight 90° edge: (1 − π/4) r² L and c² L / 2. Circular 90° edge: Pappus with
  the corner's centroid r (10 − 3π) / (3 (4 − π)) (fillet) or c/3 (chamfer) from the sharp edge, inward for a
  cylinder's rim and outward for a hole's mouth.
- **Feature volumes are signed and need independence.** `spec.json` `"features"` measures full − replay-without, so
  a cut is negative. A feature that later selectors depend on (the corner fillets under the rim chamfer) cannot be
  measured this way: replaying without it changes the later feature too.
- **Helix.** `OCC.makeHelix(pitch, height, radius, 0, lefthand)` is one wire; a circle at its start, normal to its
  tangent, swept with `makePipeShell([circle], True, True)` (Frenet) gives a solid within 2 ppm of
  π d²/4 × the helix length. The ends are square to the wire, so the height is `height` + d cos α.
- **Thin round wire in STL.** At the pipeline's 0.05 mm deflection the Ø2 spring's STL is 1.7 % under its volume;
  `example_spring` allows 2 % for `export.stl`.

## Parity sweep (2026-11-08)

All **90** projects with a `model.py` and `spec.json` pass their existing specs under `--backend freecad`
(`--no-promote`, so the SolidWorks exports in the repo were left alone). The first sweep found 14 failures, all
fixed by the three points above. Typical run 3 s end to end; the slowest are `airmn_fan_housing` (1132 holes,
84 s), `rpi_dac_pro` (17 s) and the boards (10–12 s).

## Assemblies (scripts/fc/fc_assembly.py)

- Each component is the part's promoted STEP (`projects/<part>/exports/<part>.step`, from either backend) read once
  with `Part.read`, copied and placed with `transformShape(Matrix)`. `at` + `rot_z` and the row-vector `xform` map
  to the same 4 × 4 as SolidWorks' `Transform2`, so `assembly.json` files need no change.
- Interference: pairwise `common().Volume > 1e-3 mm³` after a bounding-box prefilter. Touching faces give zero,
  as with SolidWorks' coincidence off. grindmn (31 components): about 40 s including the Blender views.
- The assembly STEP comes from `Import.export` of one `Part::Feature` per component, so it imports into Blender
  (and FreeCAD) as separate products.

## Check renders

- Headless FreeCAD has no 3D view, so the pipeline renders the exported STL in Blender
  (`scripts/blender/bl_check_views.py`: Workbench, orthographic, the same Z-up isometric/top/front/right as
  `swlib.render`). About 2 s for four 800 × 800 views.

## Rendering adapter (render_adapters/freecad.py)

- Verified end to end with `tests/test_render_e2e.py` on an App::Part holding a box and three App::Links to one
  cylinder: 2 unique parts, 4 components, bbox exact, all previews, approval gates and finals pass.
- `Part.makeCompound(...).exportStep` writes **one** STEP product, which the Blender STEP importer turns into one
  mesh. `Import.export([one Part::Feature per component], path)` writes one product each, as the cross-check needs.

## Blender on Linux

- The apt Blender (4.0.2) is too old for the STEP Importer (5.1+). Blender 5.2.3 LTS portable
  (`blender-5.2.3-linux-x64.tar.xz`, SHA-256 checked) unpacked into `~/Tools` is found automatically by
  `render_config.py`.
- STEP Importer 1.2.1 has a separate Linux build: `add-on-step-importer-v1.2.1-linux-x64.zip`, installed with
  `blender --command extension install-file -r user_default -e <zip>`.
- Cycles lists the GTX 1650 SUPER as a CUDA device here, unlike the Windows machine's GT 640.
