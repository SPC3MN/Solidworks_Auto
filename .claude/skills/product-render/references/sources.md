# CAD sources and adapters

Every source ends in the same product package, so the rest of the pipeline never knows where a model came from:

```
<folder>/render/export/product_manifest.json     schema 2.0 (scripts/render_adapters/common.py)
<folder>/render/export/geometry/parts/*          one file per unique part, in part coordinates
<folder>/render/export/geometry/<asm>.step|source.*   the whole product, for the import cross-check
```

## Which route for which CAD system

| CAD system | Best route | Notes |
|---|---|---|
| SolidWorks | `export model.SLDASM` (solidworks adapter) | Live COM: ids = `Name2`, kernel bboxes, SolidWorks materials. AP214 (AP242 needs MBD). |
| FreeCAD | `export model.FCStd` (freecad adapter) | Headless FreeCADCmd: Part/PartDesign bodies, App::Part, groups, App::Link (incl. arrays), Assembly 1.x. Colours from GuiDocument.xml, material from `ShapeMaterial` (1.0+). Not yet run against a real FreeCAD here; if it fails, use the STEP route. |
| FreeCAD (fallback) | File > Export > STEP (`.step`) → `export model.step` | Keeps names, hierarchy, placements and colours. |
| Onshape | Export assembly as STEP (or glTF) | STEP keeps the instance tree. |
| Fusion | Export > STEP (or OBJ/FBX for appearances) | |
| Inventor, Creo, CATIA, NX, Solid Edge | STEP AP214/AP242 | Any AP works; the importer tessellates the B-rep. |
| Vendor models (McMaster, TraceParts, GrabCAD) | the STEP they offer | Prefer STEP over STL. |
| Mesh-only (scans, 3D-print files) | `export part.stl --units mm --up Z --expect-size ...` | No names or instances; one part per object. |

**Prefer STEP**: it carries exact geometry (tessellated at import with `--tol-linear`), units, names, the assembly
tree, instances and colours. glTF/GLB is next best (metres, Y-up by definition, names, instancing, materials).
FBX and USD carry units. OBJ, STL and PLY carry neither units nor an up axis, so pass `--units` and `--up`.

## What the file adapter recovers (scripts/blender/bl_ingest.py)

- Every mesh object becomes a component; its world matrix is the transform (mm, Z-up).
- Empties above components become subassemblies; a single top-level empty is the product root.
- Instances: STEP and glTF keep each instance's geometry in part coordinates, so components whose meshes match (same
  base name without Blender's `.001`, same vertex/face count, same local bbox to 0.01 mm) become one part. Verified on
  grindmn's STEP: 24 unique parts and 29 components, exactly what SolidWorks reports.
- Placeholder material names (`mat_0`, `Material.001`) are ignored; real ones ("Aluminum 6061", "ABS black") go
  through `cad_material_map`. A colour or material shared by every part (an uncoloured model's default) is dropped.
- The source file is copied to `render/export/geometry/source.<ext>`, so the workspace is self-contained.

## Validation strength

`manifest.validation.reference`:
- `cad_kernel` (SolidWorks, FreeCAD): expected sizes come from the CAD system; the import checks prove scale,
  orientation, placement and completeness.
- `source_file` (file adapter): expected sizes come from the imported file; the checks prove the round trip and
  placement only. Confirm the scale with `--expect-size` (a known overall dimension) or by asking the user.

## Adding an adapter

1. `scripts/render_adapters/<name>.py` with `EXTENSIONS = (".ext",)` and
   `export(target, render_dir, lib, **options) -> manifest`.
2. Build the manifest with `common.new_manifest`, `common.part_entry` (geometry in any format in `common.FORMATS`,
   bbox in part coordinates, mm) and `common.component_entry` (4×4 column-vector transform, translation in mm, Z-up).
   Convert units and axes in the adapter; the manifest is always mm / Z-up.
3. Measure bboxes with the CAD kernel when possible and set `reference="cad_kernel"`; otherwise `"source_file"`.
4. Register it in `scripts/render_adapters/__init__.py` (`ADAPTERS`, `NAMES`, `detect`).
5. Add a unit test that builds a manifest from canned data (see `FreeCADAdapter.test_manifest_from_dump`), then run
   `tests/test_render_e2e.py <a real file>`.
Never claim an adapter works before the end-to-end test passed on a real file from that CAD system.
