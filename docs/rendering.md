# Photorealistic rendering: architecture and verified facts

How a 3D CAD model, from any source, becomes photorealistic images in Blender Cycles. The workflow for the agent
is the project skill `.claude/skills/product-render` (`/product-render`). This page explains why it is built the
way it is and records what was verified (first on 2026-11-08; the source-neutral adapters later the same day).

## Architecture

```
CAD source (authoritative)        adapters (scripts/render_adapters)        Blender 5.2 (headless)
.SLDASM/.SLDPRT ── solidworks.py (COM) ─┐
.FCStd ─────────── freecad.py ──────────┼─► product package ──────────► bl_import.py ──► <asm>_cad.blend
   (FreeCADCmd + freecad_dump.py)       │   manifest (schema 2.0)          │ validate      (never edited later)
.step .glb .obj .stl ─ mesh_file.py ────┘   + geometry/parts/*             ▼
   .ply .fbx .usd      (bl_ingest.py)                                   bl_scene.py ──► previews / finals
                                        render_cli.py: init → scene.json,  materials, studio, environments,
                                        preview, approve (hash), final     cameras, exploded/technical
```

- **Adapters are the only source-specific code.** Each turns one CAD source into the same product package: the
  manifest plus one geometry file per unique part, in part coordinates. Blender, the materials, the scenes, the
  approval gate and the tests know nothing about SolidWorks or FreeCAD. A new CAD system is one module
  (`references/sources.md` in the skill: "Adding an adapter"), or no code at all when it can export STEP.
- **Two skills, one direction.** `model-from-photo` (and the assembly and drawing scripts) own the geometry.
  `product-render` reads exports and never writes CAD.
- **One state file.** `render/settings/scene.json` holds every look decision: materials, lighting, environment,
  shots and quality. Previews and finals are both built from it. The approval stores its hash together with the
  render libraries (materials, lighting, cameras), and `final` refuses to run on a mismatch. Settings key on part
  ids and component ids/labels, so they survive a re-export and carry across sources that keep the same names.
- **Cached geometry.** Tessellation and file reading run once (`import`). Each preview opens the cached
  `_cad.blend` and rebuilds the look, which takes seconds.
- **Per-part import, manifest placement.** Each unique part is imported once, and every instance is an object
  sharing that mesh with the manifest transform: stable ids (`cad_id`, `cad_part`, `cad_parent`, `cad_label`
  custom properties), repeated instances with separate materials, exact control over hierarchy and placement.
  The whole-product file, when there is one, is imported once more as an independent cross-check.
- **Geometry formats** (`scripts/blender/bl_formats.py`): `step` (STEP Importer extension), `gltf` (glTF/GLB),
  `obj`, `stl`, `ply` (need `scale_to_m` and the file's up axis), `fbx`, `usd`. All come out in metres, Z-up.

## Product manifest (`render/export/product_manifest.json`, schema 2.0)

Defined and validated in `scripts/render_adapters/common.py` (`new_manifest`, `part_entry`, `component_entry`,
`finish`, `validate`). Schema 1.0 files (the first SolidWorks-only version) are upgraded in memory by `common.upgrade`.

```json
{"schema_version": "2.0", "project": "grindmn", "assembly": "grindmn",
 "source": {"adapter": "solidworks | freecad | file", "application": "SOLIDWORKS", "application_version": "...",
            "file": ".../grindmn.SLDASM", "exported": "...", "details": {"step_protocol": "AP214", ...}},
 "units": {"length": "mm", "up_axis": "Z"},
 "bbox_mm": {"min": [...], "max": [...], "size": [129.0, 68.4, 235.0]},
 "hierarchy": [{"id": "grindmn", "parent": null, "kind": "assembly"}, {"id": "sub-1", "parent": "grindmn", "kind": "subassembly"}],
 "parts": {"grindmn_screw_m3x8": {"geometry": {"file": "export/geometry/parts/grindmn_screw_m3x8.step", "format": "step",
                                               "scale_to_m": null, "up_axis": "Z"},
           "bbox_mm": {"min": [...], "max": [...]}, "source_material": "", "source_color": "#RRGGBB | null",
           "material": {"material": "stainless_steel", "source": "name_rule", "confidence": "low"}}},
 "components": [{"id": "grindmn_screw_m3x8-1", "label": "arm_screw_1", "part": "grindmn_screw_m3x8", "parent": "grindmn",
                 "transform": [[1,0,0,-6],[0,1,0,0],[0,0,1,143],[0,0,0,1]], "visible": true, "suppressed": false,
                 "world_bbox_mm": [[...], [...]], "occurrence": 1, "source": {"sw_path": "..."}}],
 "geometry": {"assembly": {"file": "export/geometry/grindmn.step", "format": "step"}},
 "exploded": {"method": "from_assembly | auto_axial", "offsets_mm": {"grindmn_screw_m3x8-1": [0, 0, 309.5]}},
 "validation": {"reference": "cad_kernel | source_file", "note": "..."}}
```

- Always mm and Z-up; adapters convert. `transform` is a 4×4 matrix in the column-vector convention, translation in
  mm, relative to the product root. `world_bbox_mm` is the part bbox carried through the transform (the import
  check compares the same quantity, so it is exact for any rotation).
- Component ids come from the source: SolidWorks `Name2` (`part-2`, `sub-1/part-1`), the FreeCAD object path
  (`Assembly/Link001`), or the node path in a STEP/glTF file (`fasteners/screw0`). `label` comes from this repo's
  `assembly.json` where one exists. `occurrence` is the source's instance number when it has one.
- `validation.reference` says how strong the import checks are: `cad_kernel` when the CAD system measured the
  bboxes (SolidWorks, FreeCAD/OpenCASCADE), `source_file` when they come from the file that is imported (the
  file adapter), in which case `--expect-size` confirms the scale.
- Material proposals: the CAD material name through `cad_material_map`, then part-name rules, then a default, each
  with `source` and `confidence`. Overrides live in scene.json and survive a re-export.

## Verified facts

**Source-neutral path** (2026-11-08):
- grindmn's assembly STEP through the file adapter gave 24 unique parts and 29 components with bbox
  129 × 68.4 × 235 mm, identical to the SolidWorks adapter, and every import check passed.
- The STEP Importer gives each instance its own mesh (no sharing) but keeps it in part coordinates and names
  repeats `name.001`; instances are therefore rebuilt from base name + vertex/face count + local bbox.
- A generated glTF with a nested subassembly and three rotated instances of one mesh: 2 parts, 4 components,
  hierarchy and placement checks pass; the glTF material name "Aluminum 6061" mapped to `aluminium_raw`.
- An STL with `--units m` was caught by `--expect-size` (1000× too large); with `--units mm` it imported at
  340 × 600 × 6.35 mm as specified.
- Blender 5.2 importer options were read from the operators' RNA: `wm.obj_import`/`stl_import`/`ply_import`
  (`global_scale`, `forward_axis`, `up_axis`), `import_scene.gltf`, `import_scene.fbx`, `wm.usd_import`
  (`apply_unit_conversion_scale`), `export_scene.gltf` (`export_format`, `use_selection`, `export_yup`).
- The FreeCAD adapter's host side (manifest building, GuiDocument.xml colours) is unit-tested; the part that runs
  inside FreeCAD (`freecad_dump.py`) has **not** been run against a real FreeCAD yet (none installed on the
  development machine). Its fallback, STEP exported from FreeCAD through the file adapter, is the verified path.

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

Only STEP sources need the extension: glTF, OBJ, STL, PLY, FBX and USD use Blender's built-in importers.


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
- CAD colours are recorded per part (`source_color`) but used only with `materials.use_source_colors`; a colour every
  part shares is treated as a default appearance and dropped. Materials otherwise come from the requirements or rules.
- The file adapter cannot know the units of OBJ/STL/PLY or prove any file's scale on its own: `--units`, `--up` and
  `--expect-size` cover that. Mesh formats keep the tessellation they were saved with.
- The FreeCAD adapter handles Part/PartDesign bodies, App::Part, groups, App::Link (arrays included) and the 1.x
  Assembly; link scale, configuration tables and external link documents that FreeCAD cannot open are not handled
  (the bbox check against FreeCAD's own evaluation stops the export when the walk misses something).
