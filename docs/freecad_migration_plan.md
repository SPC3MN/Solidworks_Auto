# Migration plan: SolidWorks → FreeCAD (with Blender rendering kept)

Status: **plan only** (2026-11-08). FreeCAD is not installed on this machine yet; nothing
below has been run against FreeCAD on Windows. Items marked **verify** must be proven by
the phase 0 probe before code depends on them. The FreeCAD 1.1.4 facts that *were*
verified (on macOS) are in [freecad_prototype_findings.md](freecad_prototype_findings.md).

Target stack: FreeCAD 1.1.4 (portable 7z, `C:\Users\admin\Tools\FreeCAD-1.1.4`, its own
Python 3.11) as the authoritative CAD, TechDraw for drawings, STEP AP242 to Blender 5.2.3 +
Cycles (already installed, `product-render` skill). No build123d (see §9).

---

## 1. What exists today (inventory)

| Layer | Files | SolidWorks coupling |
|---|---|---|
| Feature library | `scripts/swlib.py`: profiles `rect/circle/polygon/slot/path`, `Part.extrude/cut/shell/fillet/sweep/circular_pattern/link`, `render()` | **Total.** Profiles are closures that draw into a SolidWorks `SketchManager`; features are COM calls. |
| Geometry generators | `details.py` (package/port kinds), `board_build.py`, `encoder_build.py`, `cable_build.py`, `panel_parts.py`, `x8020_parts.py`, `projects/grindmn/grindmn_parts.py`, per-project `design/model.py` | **Light.** They compute op lists `(name, op, profiles, z0, h, volume, axis)` plus exact `expected()` volumes, then call `swlib.Part`. Only the last step is CAD-specific. |
| Pipeline | `pipeline.py`: build → measure (bbox, volume, bodies) → feature-volume checks by suppression → render → STEP/STL export → reopen STEP → STL volume and watertightness in pure Python → promote | Measuring, saving, suppressing and rendering go through COM; the checks, report format and promotion logic are neutral. |
| Specs | `projects/*/validation/spec.json`, `requirements.md`, `params.json`, `layout.json` | **None.** Expected values come from hand arithmetic, not from a CAD run. This is the parity test suite for the migration. |
| Assemblies | `assembly.py` (from `assembly.json`: insert, `Transform2`, fix, interference, bbox, STEP, renders), `asm_capture.py` / `asm_simplify.py` / `frame_check.py` (vendor SLDASM → simplified 80/20 parts) | `assembly.json` is neutral; building and checking are COM. `asm_capture` reads *SolidWorks* source assemblies and stays SolidWorks-only (or STEP-input, §6.4). |
| Drawings | `drawing.py` + `drawing.json` + `dimensioned-drawing` skill: Z-up named views, A3 layout, standard scales, edge picking by model point → `ModelToViewTransform`, read-back of measured values, overlap resolution, title block, section A-A | View creation, picking and read-back are COM; the layout maths, scale table, overlap resolver and `drawing.json` schema are neutral. |
| Rendering | `render_export.py` (SolidWorks → STEP + `product_manifest.json`), `scripts/blender/*`, `render_cli.py`, `libraries/render/*`, `product-render` skill | Only `render_export.py` touches SolidWorks. Everything from the manifest onward is CAD-neutral. |
| Skills | `model-from-photo`, `dimensioned-drawing`, `product-render` | Instructions name SolidWorks files, gotchas and commands. |

Scale of the job: 94 projects and 10 assemblies, all with specs. Most projects go through a
shared builder, so porting the ~6 builders covers most parts.

## 2. Key decisions

1. **Port the backend, not the generators.** Turn profiles into plain data (a small geometry
   description) and put two backends behind one `Part` interface: `swlib` (SolidWorks) and
   `fclib` (FreeCAD). The op-list generators, `expected()` maths, specs and project layout stay
   as they are. This is the one refactor that keeps all 94 projects portable.
2. **Keep the project layout.** `projects/<name>/design/<name>.FCStd` replaces `.SLDPRT`, and
   the rest stays (`parameters/`, `validation/`, `exports/`, `renders/`, `drawing/`, `render/`).
   The brief's `CAD/ … Rendering/ … metadata/` tree maps onto it as follows: `CAD/native` →
   `design/`, `CAD/exports` → `exports/`, `CAD/drawings` → `drawing/`, `Rendering` → `render/`,
   `metadata/product_manifest.json` → `render/export/product_manifest.json`,
   `metadata/assumptions.md` → `requirements.md` (it already holds assumptions), and
   `reports/` → `validation/history/`. Moving 94 projects would break the history for no gain.
3. **Two interpreters, JSON in between.** The `.venv` Python (3.14) orchestrates. FreeCAD
   scripts run in `FreeCADCmd.exe` (Python 3.11), and Blender scripts run in Blender
   (Python 3.11). Each run receives a JSON job file and writes a JSON report; there are no
   shared imports across interpreters. Software paths are found the way `render_config.py`
   finds Blender (env var → `config/*.local.json` → `~/Tools/…` → PATH).
4. **Modelling strategy per geometry:**
   - **Mechanical parts** (enclosures, brackets, plates, turned parts): a PartDesign `Body`
     with fully constrained sketches attached to datum planes. Driving dimensions are bound to
     a `Spreadsheet` of named parameters (the equivalent of today's Global Variables; verified
     in the prototype). Features are Pad, Pocket, Revolution/Groove, Fillet/Chamfer, LinearPattern,
     PolarPattern and Mirrored.
   - **Turned parts** get a real `revolve` op (a Revolution of the half profile) instead of today's
     stacked extrudes. This is new capability, and grindmn's volume formulas still apply.
   - **Populated boards** (hundreds of package details): one Body, with the board outline as a
     parametric Pad and the details as Part-workbench solids fused per group into a
     `PartDesign::FeatureBase`/`BaseFeature`. They are not parametric in the GUI, as today
     (`swlib` already says "Other changes need a rerun of `model.py`"). **Verify** recompute time
     against a 300-feature PartDesign tree; fall back to this split if it is slow.
5. **Validation stays spec-driven.** The same `spec.json` files are checked against FreeCAD
   geometry. A FreeCAD part "passes" only when its spec passes, the same rule as now.
6. **SolidWorks stays working until parity.** `--backend solidworks|freecad` on `pipeline.py`
   and `assembly.py`, with SolidWorks the default until phase 7 signs off. No SolidWorks file
   or script is deleted in this migration.

## 3. SolidWorks vs FreeCAD: differences the code must handle

| Topic | SolidWorks (today) | FreeCAD 1.1 | Consequence |
|---|---|---|---|
| Parameters | Global Variables + equations (`"D1@Sketch1"`) | Spreadsheet aliases + expressions (`Sheet.outer_length`) | Aliases can't be unit names (`mm`, `rad`, `deg`, `in`); validate names. |
| Sketch status | Read `GetConstrainedStatus` | `sketch.solve()`, `FullyConstrained`, `getMalformedConstraints()` | Under-constraint detection is easier and becomes a pipeline check. |
| Face/edge picking | Select by point (`SelectByID2`) | Edge names (`Edge12`) are topological and shift when the model changes (TNP is mitigated in 1.0+, not gone) | Pick by geometry at build time (nearest edge to a point, filtered by type), as swlib does, and keep fillets and chamfers late in the tree. |
| Blind cut direction | Against the plane normal by default | Pocket goes into the support; `Reversed` flips it | `fclib.cut()` takes the same `down=` meaning and must reproduce swlib's verified directions. Test each plane family. |
| Plane families | Front/Top/Right with sign maps in `PLANE_FAMILIES` | XY/XZ/YZ datum planes, with an attachment offset for z0 | Re-derive the (a, b) → model map per family and test it with bounding boxes, as was done for SolidWorks. |
| Partly overlapping sketch edges | Rejected (findings) | Usually accepted by OCCT, but can produce invalid solids | The `shape.isValid()` check catches it. |
| Assemblies | `AddComponent5` + `Transform2`, `FixComponent` | Built-in Assembly workbench (1.0+): `App::Link` to part files + `Placement`, "Grounded" joints | Placement by coordinates maps 1:1, and `xform` rows map to `Placement(Matrix)`. Real mates (joints) are possible, but only "grounded" is needed now. **Verify** scripting the Assembly WB headless. |
| Interference | `InterferenceDetectionManager` | `a.common(b).Volume` per pair, with a bbox pre-filter | Implement this ourselves; touching faces give about 0 volume. Use a tolerance of 1e-6 mm³ and keep the `allowed_interference` semantics. |
| STEP export | AP203/AP214; AP242 only with an MBD licence (`PublishSTEP242File` → error 4) | OCCT writes **AP242** (`Import` prefs `Scheme = AP242DIS`), with names, colours and assembly structure | AP242 becomes the default, an improvement. **Verify** the scheme and colour/name output headless. |
| Renders | `SaveAs3` PNG of the viewport | Headless FreeCAD has no viewport; `FreeCADGui` needs the GUI | Pipeline check renders move to Blender (Workbench engine, seconds per view) using the STEP just exported, which reuses `scripts/blender`. |
| Drawings | SLDDRW → PDF natively | TechDraw; the prototype found PDF export needs the GUI | **Verify** in 1.1.4: (a) `TechDraw` SVG export headless, then PDF via a GUI run (`FreeCAD.exe` running a macro, then quit), or (b) SVG → PDF without extra tools. Pick (a) if it works. |
| Materials | Part material (here always the template's "Steel") | Materials system (1.0+): `ShapeMaterial` on bodies and Material cards | `fc_export` writes the engineering material into the manifest. The render finish is still chosen separately (aluminium can be bead-blasted, anodised or powder-coated). |
| Licence, concurrency | One SolidWorks instance shared with other sessions; focus stealing | One headless process per job | Removes the "another session stole focus" class of failures, and jobs can run in parallel. |

## 4. Target module layout

Adapted from the brief to this repo, with no files that only re-export something.

```
scripts/
  cad/
    profiles.py        # NEW  profile data: Rect, Circle, Polygon, Slot, Path, Ring (+ area(), for expected())
    backend.py         # NEW  Part protocol + get_backend("solidworks"|"freecad")
  swlib.py             # KEEP SolidWorks backend; profiles become data, drawn by a sw_draw(sm) adapter
  fc/                  # NEW  runs inside FreeCADCmd (Python 3.11)
    fclib.py           #   Part backend: Body, datum planes, constrained sketches, Pad/Pocket/
                       #   Revolution/Fillet/Chamfer/patterns, spreadsheet binding
    fc_job.py          #   entry point: read job JSON -> build/measure/export/drawing -> report JSON
    fc_validate.py     #   isValid, solids, bbox, volume, area, sketch status, recompute errors,
                       #   recompute-twice stability, pairwise interference, holes and wall thickness
    fc_assembly.py     #   assembly.json -> assembly FCStd with App::Link + Placement, grounded
    fc_drawing.py      #   drawing.json -> TechDraw page, views, section, detail, dims, centre marks
    fc_export.py       #   STEP AP242 (part + assembly), STL/3MF, product_manifest.json
  freecad_run.py       # NEW  venv side: find FreeCADCmd, write the job, run it with a timeout, read the report
  pipeline.py          # CHANGE --backend; measuring/exporting through the backend; Blender check renders
  assembly.py          # CHANGE --backend freecad -> fc_assembly via freecad_run
  drawing.py           # CHANGE split neutral layout code from SolidWorks calls; --backend freecad -> fc_drawing
  render_export.py     # KEEP SolidWorks exporter; fc_export writes the same manifest schema
templates/drawings/    # NEW  A3/A4 landscape SVG templates with editable fields
config/freecad.local.json  # NEW (gitignored) FreeCADCmd path
```

Blender (`scripts/blender/*`, `render_cli.py`, `libraries/render/*`) is **unchanged**: the
manifest is the contract. `product-render` only needs its export step to call `fc_export` when
the project's native file is `.FCStd`.

## 5. Phases

Each phase ends with a check that must pass before the next phase starts.

**Phase 0: install and probe (≈ half a day).** Download FreeCAD 1.1.4 portable (418 MB, SHA-256
from the release) to `~/Tools`. Write `scripts/fc/probe.py` and record the results in
`docs/freecad_findings.md`:
- `FreeCADCmd.exe` runs a script with arguments.
- Constrained sketch + Pad + Pocket on all three plane families: bboxes match the swlib sign maps.
- Spreadsheet-bound dimensions: an edit followed by recompute changes the bbox.
- Fillet by point pick.
- STEP export as AP242DIS: check `FILE_SCHEMA`, and that names and colours survive into the Blender importer.
- STL/3MF export.
- Assembly WB: links, placement and a grounded joint, headless.
- TechDraw: view, section, detail, dimension and centre mark headless; check which of SVG and PDF exports headless and which need the GUI.
- Recompute time of a 300-feature body.
- *Check:* every **verify** item in §3 resolved, or replaced by a decided fallback.

**Phase 1: CAD-neutral profiles (≈ 1 day, no behaviour change).** Add `cad/profiles.py`.
`swlib.rect()` etc. return profile objects that `swlib` draws with the existing calls. Port the
custom closures (`details.py`'s `ring`, cable paths).
- *Check:* rerun a regression set of about 12 projects (one per builder, plus grindmn and
  example_tray) through SolidWorks. All reports pass with identical volumes.

**Phase 2: FreeCAD part backend (≈ 3–4 days).** `fclib.Part` with the swlib method set
(`extrude/cut/shell/fillet/sweep/circular_pattern/link`) plus `revolve`, `chamfer`,
`linear_pattern` and `mirror`.
- Sketches are constrained: coincident, horizontal/vertical and tangent constraints, with
  distance/radius constraints named after their parameters.
- `fc_validate` reports per feature: valid/invalid, constraint status and error text, so the
  agent can act on it (for example `Pocket003: sketch Sketch004 under-constrained (2 DoF);
  profile edge overlaps model edge`).
- *Check:* `example_box`, `example_tray`, `encoder_ec11`, `grindmn_shaft` and `rpi5` pass their
  *existing* spec.json under `--backend freecad`.

**Phase 3: pipeline on FreeCAD (≈ 2 days).**
- `pipeline.py --backend freecad`: build in `.staging/<stamp>/`, then measure.
- Feature-volume checks: toggle `Suppressed` (PartDesign 1.1, **verify**) or recompute
  without the feature.
- Export STEP AP242, STL and 3MF. Reopen the STEP with `Part.read` and compare the volume.
  STL volume and watertightness use the existing pure-Python check. Render check views in Blender.
- Add the checks the SolidWorks version never had: recompute twice and compare the
  geometry hash, under-constrained sketches, surface area, holes (test 3) and wall thickness
  (test 4). These are straightforward on OCCT shapes (cylindrical faces, `distToShape`).
- *Check:* architecture tests 1–9 pass (the 8 listed in architecture.md plus interference).

**Phase 4: assemblies (≈ 1–2 days).**
- `fc_assembly` reads `assembly.json` unchanged (`at`, `rot_z`, `xform`, labels, lines, views).
- Component identity: each link is named after its label or `<part>-<n>`, mirroring the
  SolidWorks `Name2`.
- Interference is checked pairwise against `allowed_interference` / `baseline_interference`.
- *Check:* `pi5_dac_hat`, `grindmn` and `grindmn_exploded` match their expected bboxes and interference lists.

**Phase 5: TechDraw drawings (≈ 3 days).**
- `fc_drawing` reads `drawing.json` unchanged and reuses the neutral parts of `drawing.py`:
  the layout and scale table, the overlap resolver, the title-block fields.
- Views: projection group in third angle with Z-up directions, isometric, section A-A, detail
  views, automatic arc centre marks and centrelines.
- Dimensions: pick each edge by mapping model points into view coordinates, then read back the
  measured value and compare it with `expect` (the same safety net as now).
- Title block from an SVG template: name, part number, revision, material, units, general
  tolerances, projection, scale, date.
- Output: `drawing/<name>.FCStd|.svg|.pdf`.
- *Check:* the three existing drawings (rpi5 and two grindmn machining drawings) regenerate,
  with every dimension within 0.01 mm.

**Phase 6: rendering hand-off (≈ 1 day).**
- `fc_export.py` writes STEP AP242 (assembly + one file per unique part) and
  `product_manifest.json` in the **same schema** as `render_export.py`:
  - component id is the link name, labels as now, transforms from the global `Placement`
    (4×4, mm);
  - `sw_material` becomes `cad_material`, filled from `ShapeMaterial`;
  - explode offsets come from the `_exploded` assembly.
- Update the `product-render` skill: pick the exporter by native file type.
- *Check:* `render_cli import` passes on the FreeCAD grindmn (29/29 components, bbox
  129 × 68.4 × 235), and a preview renders.

**Phase 7: end-to-end test, parity sweep, skills (≈ 2–3 days).**
- **Test project `projects/enclosure_test/` + `assemblies/enclosure_test/`**, an electronics
  enclosure (housing, removable lid, lid screws, internal standoffs, PCB mounting holes,
  USB-C and DC barrel openings, outer fillets, lip chamfer, wall-mount ears).
  Run it from a natural-language brief → requirements.md → params → spec → FreeCAD
  build → validation → assembly → TechDraw drawing → STEP AP242 → Blender import → materials
  → studio preview → one feedback round → approval → final render.
- **Failure tests (scripted):** a self-intersecting profile (invalid shape caught), an
  under-constrained sketch (reported with DoF), a missing FreeCAD path (clear error naming the
  config key), an export to an unwritable path (export check fails, nothing promoted), and a
  wrong parameter (spec catches it, autocorrect fixes it within 5 attempts).
- **Parity sweep:** all 94 projects under `--backend freecad`, in batches, each under a timeout.
  Report every spec failure; nothing is silently dropped.
- **Skills:** `model-from-photo` gets a backend section (FreeCAD default after sign-off; remove
  the SolidWorks-only gotchas or move them under a SolidWorks heading), `dimensioned-drawing`
  → TechDraw. Add `docs/setup.md`, `docs/freecad_findings.md`, `docs/migration_report.md` and
  `validation/enclosure_test_report.md`.
- *Check / sign-off:* the enclosure runs end to end, the failure tests behave as specified,
  and at least 95 % of the parity sweep passes, with the rest listed and explained. Only then
  does `freecad` become the default backend.

Rough total: 2½–3½ weeks of agent sessions. Phases 2 and 5 carry most of the risk.

## 6. What carries over, what is replaced, what is lost

**Retained unchanged:** all specs, requirements, params and layouts. The op-list generators
and `expected()` maths, `layout_check.py`, `asm_simplify.py`, the STL checker, the report
schema and promotion rule, `assembly.json` / `drawing.json` schemas, and the whole Blender
pipeline and material library.

**Replaced:** the `swlib` feature calls (by `fclib`), COM measuring and exporting, viewport
renders (by Blender check renders), SLDDRW drawings (by TechDraw), and `InterferenceDetectionManager`
(by OCCT booleans).

**Weaker in FreeCAD, plan for it:**
- Topological naming: fillet and chamfer picks can move after a parameter edit. Mitigation:
  pick by geometry, put fillets last, and recompute twice as a check.
- TechDraw dimension placement and look are less polished than SolidWorks; the existing
  overlap resolver is still needed.
- PDF export may need a GUI process (phase 0 decides).
- Large PartDesign trees recompute slowly (board split in §2.4).
- The Assembly WB solver is young; only grounded placement is relied on.
- No equivalent of SolidWorks' read-only open of vendor SLDASM files. `asm_capture.py` stays a
  SolidWorks tool; on a FreeCAD-only machine it would take STEP input instead (later work).

**Gained:** AP242 STEP without an MBD licence; headless, parallel and focus-proof builds; real
revolves; hole and wall-thickness checks; no licence or seat dependency.

## 7. Risks and how each is caught early

| Risk | Caught by | Fallback |
|---|---|---|
| Pocket/pad direction or plane sign maps differ from swlib | phase 0 bbox probe | per-family flip table in `fclib`, documented in findings |
| TechDraw PDF needs the GUI | phase 0 | run `FreeCAD.exe` with a macro and quit (still unattended) |
| Assembly WB not scriptable headless | phase 0 | plain `App::Part` + `App::Link` + Placement (no joints) |
| Board bodies too slow in PartDesign | phase 0 timing | Part-workbench detail solids as a BaseFeature |
| STEP colours or names lost on the way to Blender | phase 0 + phase 6 | manifest carries names and materials anyway; colour is cosmetic |
| Parity failures from tessellation or OCCT volume differences | phase 7 | spec tolerances are rel 0.001; look into anything above that, never widen it silently |

## 8. Invocation after migration (target)

```
.venv\Scripts\python scripts\pipeline.py projects\<name> --backend freecad
.venv\Scripts\python scripts\assembly.py assemblies\<name> --backend freecad
.venv\Scripts\python scripts\drawing.py projects\<name> --backend freecad
.venv\Scripts\python scripts\render_cli.py export assemblies\<name>     # picks fc_export for .FCStd
```

then the unchanged `product-render` flow: import → preview → feedback → explicit approval → final.

## 9. Not doing

- **build123d:** it sits on the same OCCT kernel FreeCAD uses, and FreeCAD already covers every
  feature in the brief. It would add a large OCP wheel to a third Python environment. Revisit it
  only if phase 0 shows PartDesign is too slow for board-scale part counts *and* the
  BaseFeature split doesn't fix it.
- Moving projects into a new `CAD/ Rendering/ metadata/` tree (§2.2).
- Converting existing `.SLDPRT` files. Parts are rebuilt from their scripts, which are the
  authoritative inputs (architecture.md).
