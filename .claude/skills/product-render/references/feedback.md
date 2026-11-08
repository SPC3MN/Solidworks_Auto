# User feedback → scene.json edits

Edit `render/settings/scene.json`. Change only what the request covers, then re-preview the shots it affects.
Material ids and finishes are listed in `materials.md`, lighting in `lighting.md`, and cameras in `cameras.md`.

| Request | Edit |
|---|---|
| "Make the aluminium more reflective" | `materials.parts.<part>.roughness`: lower it by 0.1 to 0.15 (anodised 0.34 → 0.2), or `"finish": "polished"` for a mirror |
| "Change the enclosure to matte black" | `materials.parts.<enclosure>`: `{"material": "powder_matte", "color": "#1A1A1C"}` or `"aluminium_anodized_black"` |
| "Make it brushed" | `"finish": "brushed"` (add `"brush": "linear_x"` for flat stock; the default `radial_z` suits turned parts) |
| "Only this screw in black" | `materials.components.<cad_id or label>` (it wins over `parts`) |
| "Use a brighter background" | `studio.background`: `{"type": "gradient", "color": "#FFFFFF", "color2": "#EDEDED"}`; `"solid"` or `"transparent"` (PNG alpha with a shadow catcher) |
| "Make the lighting softer" | `lighting.softness` 1.5 to 2, `lighting.fill_ratio` 1.3 |
| "More contrast" / "more dramatic" | `lighting.preset: "dramatic_premium"`, or `fill_ratio` 0.5 and `exposure` -0.3 |
| "Brighter overall" | `lighting.exposure` +0.5 (stops), or `lighting.intensity` 1.4 |
| "Warmer" / "cooler" | `lighting.warmth_kelvin` -800 / +800 |
| "Light from the other side" | `lighting.rotate` 90 (degrees around the product) |
| "Move the camera closer" | the shot's `camera_overrides.margin` (0.06 → 0.02), or a longer `focal_mm` |
| "Lower angle" / "from above" | `camera_overrides.el` (5 / 45), `camera_overrides.az` to turn it |
| "Close-up of the knob" | a shot with `"camera": "detail_closeup", "camera_overrides": {"target": "component:<label>"}` |
| "Less blur" / "more blur" | `camera_overrides.dof.fstop` higher (11) / lower (2.8); `"dof": null` turns it off |
| "Place it in a realistic laboratory" | `environment.preset: "laboratory"` and make sure an `env_hero` shot exists (`scene: "environment"`) |
| "Show the internal assembly" | a technical shot with `"xray": "auto"` (or list the housing ids), `"cutaway": {"components": "auto", "axis": "y", "keep": "+"}`, or `"exploded": true` |
| "Spread the explode more" | `technical.explode_scale` 1.5 |
| "Highlight the burr" | shot `"highlight": {"components": ["grindmn_inner_burr"], "color": "#FF7A00"}` |
| "Hide the crank" | shot `"hide": ["grindmn_crank_arm", ...]`; `"isolate": [...]` shows only the ones listed |
| "Portrait / wide image" | shot `"aspect": "4:5"` or `"16:9"`; `"resolution": [w, h]` for an exact size |
| "Bigger finals" / "TIFF" | `render.final.long_side`, `render.final.format: "TIFF"` |

The approval covers the whole file. After any edit, preview again and get a new explicit approval.
