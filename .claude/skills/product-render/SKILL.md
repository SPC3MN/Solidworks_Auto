---
name: product-render
description: Photorealistic product images of a 3D CAD model from any source (SolidWorks, FreeCAD, or a STEP / glTF / OBJ / STL / FBX / USD file from Onshape, Fusion, Inventor, Creo, CATIA or a vendor) with Blender Cycles - studio photography, exploded / see-through / cutaway technical views, environments on request - with previews the user must approve before final renders. Use when the user asks for renders, product shots, photoreal images, marketing or catalogue pictures, a hero shot or an exploded render of a model in this repo (assemblies/<name>, projects/<name>), of a CAD file they supply, or right after modelling one.
---

# 3D model → photorealistic renders (Blender Cycles)

The CAD source stays the authority on geometry. A **source adapter** turns it into a source-neutral product
package (manifest + one geometry file per unique part); everything after that (import, materials, scenes,
approval, finals) is identical for every source and never writes back. All state lives in files, so a later
session, or another computer, can carry on. Read `docs/rendering.md` before changing the scripts.

```
.venv\Scripts\python scripts\render_cli.py <command> <target>
```
`<target>` is a CAD file or a folder holding one. Everything goes to `<folder>/render/` (`--out` on `export` to choose).

| Source | Target | Adapter | Needs |
|---|---|---|---|
| SolidWorks | `.SLDASM` / `.SLDPRT`, or `assemblies/<name>`, `projects/<name>` | `solidworks` | SolidWorks running (Windows) |
| FreeCAD | `.FCStd` | `freecad` | FreeCAD (`FreeCADCmd`) |
| Anything else | `.step/.stp` (best), `.glb/.gltf`, `.fbx`, `.usd*`, `.obj/.stl/.ply` | `file` | only Blender |

How to get a good file out of each CAD system, and how to add an adapter: `references/sources.md`.

## 0. Requirements (check once per machine)

- **Blender 5.1+** (5.2.3 LTS verified), found from `BLENDER_EXE`, `config/render.local.json`
  (`{"blender": ".../blender.exe", "freecad": ".../FreeCADCmd.exe"}`, copy `config/render.example.json`),
  `~/Tools/blender-*`, Program Files, or PATH.
- The **STEP Importer** extension (v1.2.1 verified) for STEP sources:
  `blender --command extension install-file -r user_default -e <zip>`. Other formats use Blender's built-in importers.
- The CAD program only for its own adapter (`export`). Every later step needs Blender alone.
- `render_cli.py hw` reports the render device (a GPU when Cycles lists one, otherwise the CPU).

If anything is missing, say so and ask before downloading. Never substitute an untested converter (see `docs/rendering.md`).

## 1. Prepare the scene yourself (no questions needed)

1. **`export <target>`**: picks the adapter from the file type (`--source` to force it) and writes
   `render/export/product_manifest.json` plus `render/export/geometry/`.
   - A designed exploded assembly: add `--exploded-from assemblies/<name>_exploded`.
   - **OBJ / STL / PLY have no units or up axis**: pass `--units mm|cm|m|in|ft` and `--up Z|Y` (defaults mm, Z: the CAD
     convention). Ask the user if unsure: a wrong unit is a 1000× error.
   - **Scale check for files**: the `file` adapter measures expected sizes from the same file, so its import checks
     prove the round trip and placement, not the scale (`manifest.validation.reference = "source_file"`). Give one
     known overall size with `--expect-size X,Y,Z` (mm, 0 = unknown axis) whenever you have one. SolidWorks and FreeCAD
     sizes come from the CAD kernel (`"cad_kernel"`), which also proves the scale.
2. **`import <target>`**: imports every unique part once, makes instances from the manifest transforms, and validates
   the part bboxes, component placements, overall bbox, count and hierarchy, plus a cross-check against the
   whole-product file where there is one. **Stop on FAIL**: report it, never render around it.
3. **`init <target>`**: writes `render/settings/scene.json` (the scene state). It never overwrites an existing one.
4. **Materials:** read `materials._review` and the manifest proposals (`source`, `confidence`). Replace guesses
   with what the requirements say (a material/finish table in `projects/<x>/requirements.md`, the user's words)
   under `materials.parts`, with a `_src` note. When the CAD colours are meaningful (a coloured STEP, FreeCAD
   shape colours), set `materials.use_source_colors: true`. Mark anything still assumed as an assumption.
5. Pick the lighting preset and shots for the product (`references/`). **Environment shots are opt-in**: add one
   only when the user asks.
6. **`preview <target>`**: every shot at 800 px / 48 samples, a contact sheet and `render/reports/preview_latest.json`.
7. **Visual QC before showing anything:** open each preview with Read and fix what you can, up to 3 rounds: flat or
   uniform metal, blown highlights, product too small or cropped, a wrong material, floating parts, props crossing
   the product (`environment.clearance`), see-through parts that look wrong, faceting (re-import with a lower
   `--tol-linear` for STEP; mesh formats keep their own tessellation), a distracting background. Fix these in
   scene.json or the libraries, never in the CAD.

## 2. Present the previews (then wait)

Send the contact sheet and the key previews with SendUserFile, and list: the CAD source and adapter; the scene types,
lighting and cameras; the material table (marking assumptions); for file sources, whether the scale was confirmed;
the proposed final size, samples and format, with the CLI's time estimate; anything QC could not fix.
Then ask the user to approve the previews or ask for changes.

## 3. Feedback → scene changes

Turn each request into edits of `render/settings/scene.json` (`references/feedback.md` maps common phrases).
Re-preview only the affected shots with `preview <target> --shots a,b` while iterating; the **last preview before
approval must cover every shot** (`approve` refuses otherwise). Keep everything the user did not mention.
A **design change** in the CAD means `export` + `import` again; the scene settings carry over (they key on part ids),
but a new preview and a new approval are needed.

## 4. Approval and final render

- **Only an explicit approval counts** ("approved", "looks good, render the finals", "go ahead with the final").
  Silence, "nice", or a question with no yes is not approval: ask.
- Record it: `approve <target> --quote "<the user's words, verbatim>"`. It binds the hash of `scene.json` and the
  render libraries; any later edit invalidates it and `final` refuses to run. If the user stops a final or changes
  the design, withdraw it (move `settings/approval.json` to `settings/history/`).
- `final <target>` renders every shot at 2400 px / 256 samples (PNG 16-bit; `"format": "TIFF"` for TIFF). Run it in
  the background: on a CPU it takes tens of minutes per image.
- Outputs: `render/final/<category>/`, `render/final/contact_sheet.png`, `render/final/deliverables.md`,
  `render/blender/<asm>_final.blend`, `render/settings/final_<stamp>.json`. Send the images; never call a render
  final without the files existing.

## 5. Errors

| Symptom | Action |
|---|---|
| `export`: "SolidWorks is not running" / "FreeCAD not found" | Start it / set `FREECAD_CMD`. Or export STEP from that program and use the file adapter. |
| `export`: size does not match `--expect-size` | Wrong `--units` or `--up` for OBJ/STL/PLY. Fix and rerun; never render a wrongly scaled product. |
| `export` (FreeCAD): walk does not reproduce FreeCAD's bbox | An unsupported link/container. Export STEP from FreeCAD and use the file adapter. |
| `import` FAIL on part_bbox / assembly_bbox | Wrong scale or axis, or a broken file. Look in import_report.json, re-export, never ignore it. |
| `import` FAIL `import.<part>` | That part's file failed. Re-export; if it fails again, report it and do not render without the part. |
| Extension missing | Reinstall it (section 0). See docs/rendering.md for the fallback. |
| `final` says NOT APPROVED | Preview the current settings again and get the user's approval. |
| Render very slow | Lower `render.final.samples` or `long_side` only with the user's agreement (part of the approved settings). |

Keep CAD programs tidy: the adapters close every document they opened and never one the user had open.
Blender and FreeCAD run headless, so they open no windows.
