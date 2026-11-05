# Architecture (CAD-agnostic)

The design below was worked out for the FreeCAD prototype. It does not depend on
which CAD program is used, so it should carry over to SolidWorks.

## Principles

- **Scripts and parameters are the authoritative inputs.** The native CAD file
  (`.SLDPRT` / `.SLDASM`) is a generated output that can always be rebuilt from
  `parameters/params.json` + `design/model.*`.
- **Parameters live inside the CAD file as well.** Every feature dimension that
  comes from a parameter is linked to it inside the CAD document (FreeCAD used a
  Spreadsheet with aliases; the SolidWorks equivalent is Global Variables and
  Equations, or a Design Table). That way, editing a parameter by hand in the GUI
  also rebuilds the model correctly. Structural changes, such as the number of
  holes, still require rerunning the script.
- **One part per manufactured component**, plus an assembly for multi-part designs.
- **Descriptive feature names and stable references.** Build profiles as fully
  constrained sketches. Avoid selecting faces or edges by index. Put rounded
  corners in the sketch profile rather than adding edge fillets afterwards
  wherever possible.
- **Fuse first, cut once.** Combine all added material (bosses, ribs), then apply
  all cut tools (holes, vents, connector openings) together. This keeps boolean
  complexity down.
- **Never overwrite the last validated model.** Every build goes to a staging area
  and is promoted only if validation passes.
- **Never claim success without checking.** Every export is reopened and compared
  with the original geometry.

## Project layout (per design)

```
projects/<name>/
  requirements.md        # Phase A output: dims, functions, materials, process, assumptions
  references/            # photos, datasheets, supplied STEP models
  parameters/params.json # authoritative parameter values (mm)
  design/                # model script + generated native CAD files (validated only)
  validation/spec.json   # expected values, taken from the requirements
  validation/history/    # one report per build attempt (pass or fail)
  drawings/              # PDF + DXF
  exports/               # STEP, STL, 3MF
  renders/               # iso / front / side / top / section / exploded
  .staging/              # unvalidated build output (gitignored)
```

Planned top-level folders: `standards/`, `templates/` (reusable feature
functions), `libraries/` (fasteners, connectors, PCBs, materials, each with a
source and a `verified` flag), `scripts/`, `validation/`, `documentation/`,
`tests/`.

## Pipeline

1. **Build**: run the model script into `.staging/`.
2. **Validate**: write a machine-readable report (see below).
3. **If it passes**: export, generate drawings and renders, run a slicer check,
   then copy everything from staging into the real folders and archive the report.
4. **If it fails**: leave the last validated outputs untouched, archive the
   failure report, and go to autocorrection.

## Validation checks

| # | Category | Method used in the prototype design |
|---|----------|-------------------------------------|
| 1 | Solid validity | kernel validity check, one solid per component |
| 2 | Bounding dimensions | bounding box vs spec, with tolerance |
| 3 | Holes | find cylindrical faces whose surface normal points toward the axis; group by axis; compare diameter and position |
| 4 | Wall thickness | sample points on faces away from their edges, cast a ray inward along the normal, measure the length of the first solid segment |
| 5 | Clearances | minimum distance between components |
| 6 | Interference | volume of the intersection between components (must be ≈ 0) |
| 7 | Assembly fit | clearance window between mating parts (e.g. lid lip vs base) |
| 8 | Manufacturing | minimum wall, minimum hole, build volume, flat base, overhang share (FDM) |
| 9 | Export integrity | reopen STEP and STL/3MF; compare volume and bbox; mesh must be closed (watertight) |

The spec takes its expected values from **requirements** (fixed numbers), not
from parameters. A wrong parameter therefore shows up as a mismatch instead of
validating itself. A spec entry may name the parameter that drives it, e.g.
`{"bbox.x": {"expected": 120, "tol": 0.05, "param": "outer_length"}}`, and
autocorrection uses that link.

### Report shape

```json
{
  "schema_version": "1.0",
  "project": "...", "timestamp": "...", "model_file": "...",
  "status": "pass | fail | warn",
  "summary": {"passed": 0, "failed": 0, "warnings": 0},
  "components": {"Base": {"volume": 0, "bbox": [0,0,0], "is_valid": true, "holes": []}},
  "checks": [{
    "id": "bbox.Base.x", "category": "bounding_dimensions", "target": "Base",
    "status": "pass | fail | warn", "measured": 118.0, "expected": 120.0,
    "tolerance": 0.05, "message": "...",
    "hint": {"param": "outer_length", "feature": "Base_Profile"}
  }]
}
```

## Autocorrection

- **Parameter-level** (handled automatically): if a failed check names a `param`,
  adjust that parameter (bbox: add the difference; min wall: raise to the
  manufacturing minimum; hole: snap to the fastener table), rebuild, revalidate.
- **Script-level** (handled by the agent): find the failing feature, diagnose,
  edit the model script, rebuild.
- At most **5 attempts per unresolved issue**. Every attempt is logged in
  `validation/history/`. Unresolved issues are reported, never hidden.

## Agent workflow phases

A. Turn the brief into requirements; write down assumptions; ask only about
   gaps that would materially change the design.
B. Plan: list the components, coordinate system, feature sequence, critical
   dimensions, parameters, mating relationships, manufacturing limits.
C. Generate the model. D. Render it and look at it. E. Validate. F. Autocorrect.
G. Produce native files, STEP, STL, 3MF, PDF/DXF drawings, scripts, parameters,
   reports and renders.

Dimensions measured from reference images are estimates unless there is a known
scale. Supplied dimensions and datasheets are authoritative. Library entries
record their source and whether they have been verified.

## Test plan (to reimplement against SolidWorks)

1. Solid box 100×60×30. 2. Change width to 120 and confirm a clean rebuild.
3. Hollow box with 3 mm walls (check measured wall thickness). 4. Four bosses
with holes (hole detection finds all four at the right size and position).
5. Lid + base with a lip, no interference, clearance within the window.
6. Export STEP/STL, reopen, compare volumes. 7. Introduce a dimensional error
and confirm validation catches it. 8. Autocorrection fixes it within 5 attempts.
