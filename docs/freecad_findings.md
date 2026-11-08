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

## Parity sweep (2026-11-08)

All **90** projects with a `model.py` and `spec.json` pass their existing specs under `--backend freecad`
(`--no-promote`, so the SolidWorks exports in the repo were left alone). The first sweep found 14 failures, all
fixed by the three points above. Typical run 3 s end to end; the slowest are `airmn_fan_housing` (1132 holes,
84 s), `rpi_dac_pro` (17 s) and the boards (10–12 s).

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
