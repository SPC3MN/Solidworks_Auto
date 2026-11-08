# Render settings and outputs

Settings live in `scene.json → render.preview|final`:

| Key | Preview | Final | Meaning |
|---|---|---|---|
| `long_side` | 800 | 2400 | px on the long side; the shot `aspect` sets the other side (`resolution: [w, h]` overrides both) |
| `samples` | 48 | 256 | Cycles maximum samples (adaptive sampling stops earlier where clean) |
| `noise_threshold` | 0.03 | 0.01 | adaptive sampling threshold |
| `denoise` | true | true | OpenImageDenoise |
| `format` | PNG | PNG (16-bit) | or `TIFF` (16-bit, deflate) |

Fixed choices (in `bl_scene.configure`):
- AgX view transform;
- bounces: 12 total, 8 glossy, 12 transmission;
- indirect clamp 10, which removes fireflies with no visible loss;
- caustics off;
- persistent data on.

## Device

`detect_device()` tries OptiX, CUDA, HIP, oneAPI and Metal, and uses the first GPU that Cycles lists, otherwise the CPU.
The report records what it found. This PC (i7-3770, GT 640) renders on the **CPU**: the GT 640 is a Kepler card
with compute capability 3.0, which current Cycles does not support.

## Timing on this PC (CPU, 8 threads)

- A preview at 800² with 48 samples takes about 40 to 90 s per studio shot, and longer for environments and see-through parts.
- `preview` prints an estimate for the final set: preview time × the pixel ratio × the sample ratio × 0.6
  for adaptive sampling. At 2400² with 256 samples, expect about 25 to 60 min per shot.
- So run `final` in the background. To render faster, the user can agree to fewer samples or a smaller `long_side`.

## Folders (`<folder>/render/`)

```
export/product_manifest.json, export/geometry/parts/* (one file per part), export/geometry/<asm>.step | source.*
blender/<asm>_cad.blend   imported CAD only (rebuilt by `import`)
blender/<asm>.blend       last preview scene;  blender/<asm>_final.blend  final scene
previews/<category>/*.png, previews/contact_sheet.png
final/<category>/*.png|tif, final/contact_sheet.png, final/deliverables.md
settings/scene.json (state), settings/approval.json, settings/history/*, settings/final_<stamp>.json
reports/import_report.json, reports/preview_latest.json, reports/final_latest.json
```

The CAD files are only read. The `.blend` files and the previews are gitignored (they are
large and can be rebuilt). The manifest, settings, reports and final renders are kept.
