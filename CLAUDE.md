# Solidworks_Auto: notes for Claude

CAD driven from Python through a backend per CAD program: SolidWorks 2025 over COM (`.venv`,
pywin32) today, FreeCAD next (the user is moving to it; backend not built yet, see
`.claude/skills/model-from-photo/references/freecad.md`). The workflow and the geometry modules are
CAD-neutral; only the backend changes. The notes below describe the SolidWorks backend unless they say otherwise. Read
`docs/architecture.md` for the principles and `docs/solidworks_findings.md` for
verified API behaviour and gotchas before changing scripts.

Run Python as `.venv\Scripts\python`. Git is at `C:\Program Files\Git\cmd\git.exe`
(it may not be on PATH in older shells).

## Keep the CAD program tidy

The user does not want lots of open tabs. Close every document a script opens
once it is no longer needed. Save it first: projects go to their own folders,
and scratch or probe parts go to the session scratchpad. The pipeline closes
its model, the reopened STEP and any failed build. One-off diagnostic scripts
must close their parts too. Never close or discard documents the user opened
without asking.

## Photo → model workflow

The full, refined process (photos *and* part numbers, builder choice, detail
levels, assemblies) is the project skill `.claude/skills/model-from-photo`
(`/model-from-photo`). The summary below still applies.

When the user sends a picture of an object to model:

1. **Read the picture.** Identify the object, its main shapes (block, tray, plate,
   cylinder, bracket) and features (holes, slots, cut-outs, fillets, bosses, lids).
2. **Get scale.** Dimensions from a photo are estimates unless something of known
   size is in the frame (ruler, coin, credit card 85.6 × 54 mm, a known part) or
   the user gives at least one real dimension. Ask for one key dimension if none
   is available and the design depends on fit. Otherwise estimate, and label every
   estimated value as such.
3. **Ask only what would change the design materially**: what it is for, what it
   mates with, the material and process (default PLA/FDM), and any features hidden
   in the photo. Write the rest down as assumptions.
4. **Create `projects/<name>/`** following `projects/example_tray`:
   - `requirements.md`: dimensions (marked *measured*, *given* or *estimated*),
     features, material, assumptions, and the expected volume worked out by hand
     where practical.
   - `parameters/params.json`: every driving value in mm.
   - `validation/spec.json`: expected values taken from the requirements,
     not copied from params.
   - `design/model.py`: `build(app, params)` using `scripts/swlib.py`
     (`Part.extrude / cut / shell / fillet`, profiles `rect / circle / polygon / slot`).
     Order: add material first, then shell, then all cuts. Height is +Z; the
     base sketch is the Front Plane at z = 0.
5. **Run** `.venv\Scripts\python scripts\pipeline.py projects\<name>`.
6. **Look at the renders** in `projects/<name>/.staging/renders/` (isometric, top,
   front, right) next to the photo. Fix proportions or features that don't match.
7. **Autocorrect** failed checks: adjust the parameter named in `hint.param`, or
   fix `model.py`. Make at most 5 attempts per issue, and report anything left
   unresolved.
8. **Report** to the user: the renders (send them with SendUserFile), which
   dimensions are estimates, the check results, and the export paths
   (`design/*.SLDPRT`, `exports/*.step|.stl`).

Never claim success without a passing pipeline report in `validation/history/`.

## Photorealistic renders

Product imagery (Blender Cycles: studio, environments, exploded/technical) is the project skill
`.claude/skills/product-render` (`/product-render`), driven by `scripts/render_cli.py`. Background is in
`docs/rendering.md`. SolidWorks stays authoritative: Blender only reads STEP exports. Final renders need the
user's explicit approval of the previews (`render_cli.py approve`, with their words quoted).

## Library limits (extend swlib.py when a photo needs more)

- Extrudes and cuts on planes normal to Z (`axis="z"`, profile coords (x, y)) or
  normal to Y (`axis="y"`, profile coords (x, z)), e.g. connectors that stick out
  sideways. X-normal planes work too (profile coords (y, z)). `Part.sweep` makes round bars along line/arc paths (cables). No revolve or loft yet.
  `Part.circular_pattern` repeats features about Z (radial hole grids, vents). No sketches on tilted
  planes yet (angled blades need that extension).
- Keep profile edges from partly overlapping existing model edges. SolidWorks
  rejects such sketches (see findings).
- Swept-in sketches aren't dimensioned. Only extrusion depths and shell thickness
  are linked to global variables, so editing them in the GUI rebuilds the model.
  Other changes need a rerun of `model.py`.
- Faces and edges for shell and fillet are picked by a point on them. Choose
  points well away from other edges.
- Shared simple 80/20 (15 series) rails, gussets, fasteners: `scripts/x8020_parts.py`;
  existing assemblies are rebuilt with them via `asm_capture.py` / `asm_simplify.py` (see the skill).
- There are no checks yet for holes, wall thickness or interference (tests 3 to 5).
