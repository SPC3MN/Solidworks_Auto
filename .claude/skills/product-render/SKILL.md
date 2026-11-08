---
name: product-render
description: Photorealistic product images of a SolidWorks part or assembly in this repo with Blender Cycles (studio photography, realistic environments, exploded / see-through / cutaway technical views), with previews the user must approve before final renders. Use when the user asks for renders, product shots, photoreal images, marketing or catalogue pictures, a hero shot, an exploded render, or "show it in a lab / workshop / office", for an existing model (assemblies/<name>, projects/<name>) or right after modelling one.
---

# SolidWorks product → photorealistic renders (Blender Cycles)

SolidWorks stays the source of the geometry. Blender only gets meshes tessellated from STEP
files and never writes back. All state lives in files, so a later session can carry on.
Read `docs/rendering.md` for the architecture and verified facts before changing the scripts.

```
.venv\Scripts\python scripts\render_cli.py <command> <folder>
```
`<folder>` is `assemblies/<name>` (an .SLDASM) or `projects/<name>` (a part). Everything goes to `<folder>/render/`.

## 0. Requirements (check once per machine)

- **Blender 5.1 or newer** (5.2.3 LTS verified). It is found from `BLENDER_EXE`, `config/render.local.json`
  (`{"blender": "C:/.../blender.exe"}`), `~/Tools/blender-*`, Program Files, or PATH.
- The **STEP Importer** extension (v1.2.1 verified), installed with
  `blender --command extension install-file -r user_default -e <zip>`.
- **SolidWorks running**, but only for `export`. Every later step works without it.
- Run `render_cli.py hw` to report the render device. Cycles uses a GPU when it lists one, otherwise the CPU.
  This PC has a GT 640, which is too old for Cycles, so it renders on the CPU.

If anything is missing, say so and ask before downloading. Never substitute an untested converter (see the fallback in `docs/rendering.md`).

## 1. Prepare the scene yourself (no questions needed)

1. `export <folder>`: writes STEP files (AP214 with colours; AP242 needs an MBD licence, see docs) and
   `render/export/product_manifest.json`, which holds components, ids, hierarchy, transforms, proposed
   materials and explode offsets. If a designed exploded assembly exists, add
   `--exploded-from assemblies/<name>_exploded`.
2. `import <folder>`: imports every unique part once, makes instances from the manifest transforms, and
   validates the per-part bbox, the component positions, the overall bbox (which also checks scale and Z-up),
   the count and hierarchy, plus a cross-check against the whole-assembly STEP. **Stop on FAIL**: report it, never render around it.
3. `init <folder>`: writes `render/settings/scene.json` (the scene state). It never overwrites an existing one.
4. **Materials:** read `materials._review` and the manifest proposals (source and confidence). Replace guesses
   with what the requirements say (for example `projects/<x>/requirements.md`, the material and finish table) under
   `materials.parts`, adding a `_src` note. Mark anything still assumed as an assumption in your report.
5. Pick the lighting preset and the shots to fit the product (see `references/`). **Environment shots are
   opt-in**: the user does not want them by default, so add an `environment` shot only when they ask for one.
6. `preview <folder>`: renders every shot at 800 px with 48 samples, then writes a contact sheet and a report
   (`render/reports/preview_latest.json`).
7. **Visual QC before showing anything:** open each preview image with Read and fix what you can, up to 3 rounds:
   flat or uniform metal, blown highlights, a product that is too small or cropped, a wrong material on a part,
   floating parts, props hiding the product or crossing it (`environment.clearance`), see-through parts that look wrong,
   faceting on curved parts (re-import with a lower `--tol-linear`), or a distracting background.
   Fix these in scene.json or in the libraries, never in the CAD.

## 2. Present the previews (then wait)

Send the contact sheet and the key previews with SendUserFile, and list:
- the scene types and presets used, and the lighting;
- the camera list (preset, lens, angle);
- the material table (part → material / finish, marking which ones are assumptions);
- the proposed final size, samples and format, and the time estimate the CLI printed (CPU renders are slow);
- anything QC could not fix.

Then ask the user to approve the previews or ask for changes.

## 3. Feedback → scene changes

Turn each request into edits of `render/settings/scene.json` (`references/feedback.md` maps common phrases).
Re-preview only the affected shots with `preview <folder> --shots a,b` while iterating, but the
**last preview before approval must cover every shot** (`approve` refuses otherwise). Keep everything the user
did not mention. Old states are kept in `settings/history/`.

## 4. Approval and final render

- **Only an explicit approval counts**, such as "approved", "looks good, render the finals" or "go ahead with the final".
  Silence, "nice", or a question with no yes is not approval: ask.
- Record it: `approve <folder> --quote "<the user's words, verbatim>"`. The approval binds the hash of
  `scene.json` and the render libraries. Any later edit makes it invalid, and `final` then refuses to run.
- `final <folder>` renders every shot at 2400 px with 256 samples (PNG 16-bit; set `"format": "TIFF"` for TIFF),
  without asking again between shots. Run it in the background: on this CPU it takes tens of minutes per image.
- Final outputs: `render/final/<studio|environment|details|exploded|technical>/`, `render/final/contact_sheet.png`,
  `render/final/deliverables.md`, `render/blender/<asm>_final.blend` and `render/settings/final_<stamp>.json`.
- Report the outputs and send the final images. Never call a render final without the files existing.

## 5. Errors

| Symptom | Action |
|---|---|
| `export`: "SolidWorks is not running" | Ask the user to start SolidWorks. Existing exports can still be re-imported. |
| `import` FAIL on part_bbox or assembly_bbox | Wrong scale or axis, or a broken STEP. Look in import_report.json, re-export, and never ignore it. |
| `import` FAIL `import.<part>` | That part's STEP failed. Re-export it. If it fails again, report it and do not render without the part. |
| Extension missing | Reinstall it (section 0). See docs/rendering.md for the fallback. |
| `final` says NOT APPROVED | Preview the current settings again and get the user's approval. |
| Render very slow | Lower `render.final.samples` or `long_side` only with the user's agreement. They are part of the approved settings. |

Keep SolidWorks tidy: `export` closes everything it opened. Blender runs headless, so it opens no windows.
