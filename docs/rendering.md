# Photorealistic rendering: architecture and verified facts

How a SolidWorks product becomes photorealistic images in Blender Cycles. The workflow for the agent is the
project skill `.claude/skills/product-render` (`/product-render`). This page explains why it is built the way it is
and records what was verified on this machine (2026-11-08).

## Architecture

```
SolidWorks (authoritative)            .venv Python                      Blender 5.2 (headless)
.SLDASM/.SLDPRT ──read-only──► render_export.py ──► STEP + manifest ──► bl_import.py ──► <asm>_cad.blend
                                                                          │ validate      (never edited later)
                               render_cli.py (orchestrator, approval gate) ▼
                                 init → settings/scene.json ─────────► bl_scene.py ──► previews / finals
                                 preview → contact sheet, QC stats       materials, studio, environments,
                                 approve → approval.json (hash)          cameras, exploded/technical
                                 final  → only with a valid approval
```

- **Two skills, one direction.** `model-from-photo` (and the assembly and drawing scripts) own the geometry.
  `product-render` reads exports and never writes CAD. The CAD skill calls the render skill when images are wanted.
- **One state file.** `render/settings/scene.json` holds every look decision: materials, lighting, environment,
  shots and quality. Previews and finals are both built from it. The approval stores its hash together with the
  render libraries (materials, lighting, cameras). That makes "the user approved exactly this" checkable, and
  `final` refuses to run on a mismatch.
- **Cached geometry.** STEP tessellation runs once (`import`). Each preview opens the cached `_cad.blend` and
  rebuilds the look, which takes seconds, so iterations stay quick and are deterministic.
- **Per-part import, manifest placement.** Each unique part is imported from its own STEP, and every instance is an
  object sharing that mesh with the manifest transform. This gives stable ids (`sw_id` custom properties),
  repeated instances with separate materials, and exact control over hierarchy and placement. The whole-assembly
  STEP is still imported once as an independent cross-check.

## Product manifest (`render/export/product_manifest.json`)

```json
{"schema_version": "1.0", "project": "grindmn", "assembly": "grindmn", "source_cad": ".../grindmn.SLDASM",
 "units": {"length": "mm", "up_axis": "Z"},
 "step": {"assembly": "export/step/grindmn.step", "schema": "AUTOMOTIVE_DESIGN", "protocol": "AP214", ...},
 "bbox_mm": {"min": [...], "max": [...], "size": [129.0, 68.4, 235.0]},
 "hierarchy": [{"id": "grindmn", "parent": null, "kind": "assembly"}, {"id": "sub-1", "parent": "grindmn", "kind": "subassembly"}],
 "parts": {"grindmn_screw_m3x8": {"step": "export/step/parts/grindmn_screw_m3x8.step", "bbox_mm": {...},
           "sw_material": "...", "sw_appearance": {...}, "material": {"material": "stainless_steel", "source": "name_rule", "confidence": "low"}}},
 "components": [{"id": "grindmn_screw_m3x8-1", "label": "arm_screw_1", "part": "grindmn_screw_m3x8", "parent": "grindmn",
                 "transform": [[1,0,0,-6],[0,1,0,0],[0,0,1,143],[0,0,0,1]], "visible": true, "suppressed": false,
                 "world_bbox_mm": [[...], [...]]}],
 "exploded": {"method": "from_assembly | auto_axial", "offsets_mm": {"grindmn_screw_m3x8-1": [0, 0, 309.5]}}}
```

- `id` is the SolidWorks `Name2` (for example `part-2`, or `sub-1/part-1` when nested). It is unique and stays the same while the
  assembly is not restructured. `label` comes from `assembly.json` where one exists.
- `transform`: a 4×4 matrix in the column-vector convention, translation in mm, relative to the top assembly. It is
  converted from `Component2.Transform2.ArrayData`, which is a row-vector rotation with translation in metres.
- Material proposals: the SolidWorks material through a map, then part-name rules, then a default, each with
  `source` and `confidence`. Overrides live in scene.json and survive a re-export.

## Verified facts

**SolidWorks STEP export** (SOLIDWORKS 2025 SP5, values read from `swconst.tlb`):
- `swUserPreferenceIntegerValue_e.swStepAP` = 75. Plain `SaveAs3` writes AP214 for 214
  (`FILE_SCHEMA AUTOMOTIVE_DESIGN`). For **any other value, 242 included, it silently writes AP203**
  (`CONFIG_CONTROL_DESIGN`), even though the preference reads back as 242.
- AP242 is only available through `IModelDocExtension.PublishSTEP242File(path)`. On this seat it returns
  4 = `swPublishStep242_MBDLicenseNotAvailable` (with a `.step` path it returns 1 = invalid path; it wants `.stp`).
  So the pipeline exports **AP214** with appearances on, which carries the assembly structure, names and colours.
  `--ap242` tries the MBD route first and records why it fell back.
- `swUserPreferenceToggle_e.swStepExportAppearances` = 787. The exporter sets both preferences for the run and
  restores the user's values afterwards.
- On these parts every part reports the material "Steel" and the default appearance colour (0.792, 0.820, 0.933):
  that comes from the template, not from design intent. When every part has the same material, the exporter
  treats it as unassigned.
- In late binding, `Component2.IsSuppressed` is a property, not a method.

**Blender + STEP Importer** (Blender 5.2.3 LTS, extension 1.2.1, GPL-3, which converts STEP → glTF with cascadio):
- Install: `blender --command extension install-file -r user_default -e add-on-step-importer-v1.2.1-windows-x64.zip`.
  The module is `bl_ext.user_default.step_importer` and the operator is `bpy.ops.import_scene.step`.
- Tessellation is set through **add-on preferences**, not operator arguments: `tol_linear`, `tol_angular`
  and `tol_relative`. The script sets them before importing. `tol_linear` is absolute in mm when `tol_relative=False`.
- The output is in **metres** already, and `up_axis="Y"` (the default) maps the CAD Z-up frame correctly:
  the crank arm's bbox matched SolidWorks with scale 1.0.
- `bpy.ops.wm.read_factory_settings` disables extensions; use `read_homefile(use_empty=True)` to clear the scene.
- grindmn (24 parts, 29 components): 161 k triangles at 0.01 mm / 0.1 rad, imported in 8.4 s, and every check passed.

**Render hardware here:** an Intel i7-3770 (4 cores, 8 threads), 16 GB, and an NVIDIA GeForce GT 640 (Kepler, compute
capability 3.0), which Cycles does not list (no CUDA or OptiX devices). Rendering is CPU-only.

## Fallback if the STEP Importer is unavailable

1. Check whether the installed Blender is older than 5.1 (the extension's minimum). If it is, install 5.1+ next to it as a portable zip.
2. Second route (not implemented, so evaluate before use): STEP → glTF with cascadio in a separate Python 3.12 venv
   (`pip install cascadio`, the library the extension wraps), then Blender's built-in glTF importer. It uses the same tessellator,
   so the results should match. Validate it with `bl_import.py`'s checks before trusting it.
3. Third route: SolidWorks exports per-part STL (`SaveAs3` with `.stl`, already validated by `pipeline.py` as watertight)
   and Blender's built-in STL importer. It works without add-ons, but STL has no names or colours (the manifest
   still supplies them) and is in mm, so scale by 0.001.
None of these is substituted silently. `bl_import.py` stops with an error if the extension is missing.

## Limitations (known)

- The exploded offsets from `--exploded-from` are translations only. A component that the designed exploded assembly
  also rotates keeps its assembled rotation.
- A cutaway is done in the shader (one side of a plane is made transparent, and the inside faces get a section colour).
  There are no solid section caps, and cut parts cast no shadow on the removed side.
- Environments are simple procedural sets, convincing as soft backgrounds at f/4, but they are not scanned assets.
  Drop licensed local assets in only when the user supplies them.
- Surface finishes are procedural cues (noise, streaks, layer lines). Knurling, threads and text are rendered only
  when they are modelled in the CAD.
- The parts carry no SolidWorks appearances, so every material comes from the requirements or from rules. Colours are taken
  from a STEP only when the part has a real appearance (the importer reads them, and they are recorded as `step_rgb`).
