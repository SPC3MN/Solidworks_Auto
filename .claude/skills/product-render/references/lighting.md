# Lighting, studio sets and environments

## Studio rigs (`libraries/render/lighting.json`)

Every light is an area light aimed at the product centre. Size and distance scale with the product's bbox
diagonal S, and power is set from a target irradiance (P = E·π·d²). The same preset therefore works for an
encoder or a 2 m frame.

| Preset | Look | Use for |
|---|---|---|
| `soft_commercial` | big key softbox front-left, large fill, overhead box, gentle rim; light gradient sweep | catalogue, web shop, the default |
| `dramatic_premium` | narrow strip key from the side, two strong rim strips behind, dark glossy floor, AgX Medium High Contrast | premium or hero marketing, dark metals |
| `neutral_technical` | two big boxes and a back light, bright ambient, flat grey floor | documentation, the technical scene |

Modifiers in `scene.json → lighting`: `intensity`, `softness` (light size), `fill_ratio` (every light but the key),
`warmth_kelvin`, `rotate` (degrees around Z), `exposure` (stops), `look` (an AgX look name).
The studio set is in `scene.json → studio`:
- `background.type`: `gradient` (`color` at the floor, `color2` up the wall), `solid`, or `transparent` (film alpha with a shadow-catcher floor);
- `floor.type`: `sweep` (cyclorama), `plane`, or `none`; plus `floor.color` and `floor.roughness` (low = reflective).

## Environments (`scene.json → environment.preset`): only on request

`init` adds no environment shot; the user does not want environment renders unless they ask. To add one:
`{"name": "env_hero", "scene": "environment", "camera": "environment_hero", "category": "environment"}`.

Built procedurally in `scripts/blender/bl_environments.py`. There are no downloaded assets, so nothing needs a licence.
The product is never moved. The support's top is set to the product's lowest point, and props stay out of the product's
box (checked as `environment.clearance`). Furniture keeps real-world sizes, and supports grow with the product.

| Preset | Support | Set |
|---|---|---|
| `workshop` | wooden workbench on a steel frame | pegboard wall, concrete floor, warm overhead strip, window light |
| `laboratory` | dark epoxy-resin bench on white cabinets | tiled backsplash, shelf with glass bottles, cool ceiling light |
| `industrial` | steel workstand with a tread-plate top (or the floor if the product is over 1.2 m) | concrete floor, clad wall, yellow columns, high-bay lights |
| `office` | oak desk | plaster wall, monitor and mug (only when there is room beside the product), window daylight |
| `display` | white plinth | dark gallery walls, spotlight from above, wall wash |
| `architectural` | low travertine plinth | polished-concrete floor, white walls, tall window with daylight and sun |

`environment.intensity` and `environment.exposure` brighten an environment as a whole. Use the
`environment_hero` camera (50 mm, wide margin, f/4), so the room reads but stays soft behind the product.

## QC hints

- A metal surface reads as flat grey when the world is bright and uniform: lower the world strength, or use strip lights.
- A dark product on a dark set: raise `RimL` / `RimR` with `fill_ratio`, or use a lighter `studio.background`.
- Contact shadows come from the area lights. If the product looks like it floats, check that the floor is at its lowest point (`grounded` in the report).
