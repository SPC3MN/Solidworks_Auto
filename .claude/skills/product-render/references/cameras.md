# Cameras and shots

Presets live in `libraries/render/cameras.json`. A camera looks at its target box from azimuth `az` and elevation `el`:
- `az` 0 is the product front (the camera on the -Y side), and positive `az` moves it toward +X;
- `el` 90 looks straight down.

The distance (perspective) or the ortho scale is solved exactly, so every corner of the target box fits inside the
frame with `margin` free on the tightest side. The framing report gives `bbox_fill` and `cropped` for each shot.

| Preset | Lens | Angle | Notes |
|---|---|---|---|
| `three_quarter_hero` | 85 mm | az 35, el 22 | f/8 depth of field; the main product shot |
| `low_angle_hero` | 50 mm | az 25, el 6 | looks slightly up; makes the product look heroic |
| `front_ortho`, `side_ortho`, `top_ortho` | ortho | 0/0, 90/0, top | true orthographic, no perspective |
| `detail_closeup` | 100 mm | az 30, el 25 | `target: region:top` by default; f/5.6 (f/2.8 left the knob soft) |
| `exploded_hero` | 70 mm | az 35, el 16 | frames the exploded set |
| `environment_hero` | 50 mm | az 30, el 14 | margin 0.32 so the room shows; f/4 |

## Shots (`scene.json → shots`)

```json
{"name": "hero", "scene": "studio|environment|technical", "camera": "three_quarter_hero",
 "camera_overrides": {"az": 50, "margin": 0.04, "focal_mm": 100, "dof": {"fstop": 5.6}, "target": "component:knob"},
 "category": "studio|environment|details|exploded|technical", "aspect": "1:1",
 "exploded": false, "xray": "auto", "cutaway": {"components": "auto", "axis": "y", "keep": "+"},
 "highlight": {"components": ["<id>"], "color": "#FF7A00"}, "hide": [], "isolate": []}
```

- `target`: `product`, `region:top|bottom|front|left|right` (that 30 % slab of the bbox), or `component:<cad_id or label>`.
- The depth-of-field focus is the target centre. Keep f/8 or above for whole-product shots, because at product scale f/2.8 blurs most of the product.
- Exploded positions come from the manifest:
  - a designed exploded assembly (`--exploded-from`, translation only);
  - or `auto_axial`: components ranked along the axis, each rank moved by a gap, and the largest part kept fixed.

  `technical.explode_scale` scales the gaps. The assembled objects are never moved: the exploded set is a separate collection of linked duplicates.
