# Materials

The library is `libraries/render/materials.json`, built with Blender's Principled BSDF by `scripts/blender/bl_materials.py`.
The values are **rendering presets** tuned to look right under the studio rigs. They are not measured optical data,
so never call a render physically accurate.

## Resolution order (later wins)

1. **Manifest proposal per part.** The first of these that applies:
   - the SolidWorks material through `solidworks_material_map`;
   - a part-name regex in `name_rules`;
   - the default.

   The proposal records its `source` and `confidence`. If every part has the same SolidWorks material (the template's
   "Steel"), that material is treated as unassigned.
2. `scene.json → materials.parts[<part_id>]`: the part as a whole. Fill it from the requirements.
3. `scene.json → materials.components[<sw_id or label>]`: one instance (for example one black screw among steel ones).

An assignment can set `material`, `finish`, `color` (sRGB hex) and any Principled field: `roughness`, `metallic`,
`ior`, `transmission`, `anisotropy`, `coat`, `coat_roughness`, `alpha`, `bump`, `variation`, `brush`.
Repeated instances share a mesh but each object has its own material slot (`link = OBJECT`).

## Ids

| Group | Ids |
|---|---|
| Metals | `aluminium_raw`, `aluminium_brushed`, `aluminium_anodized` (clear, bead blasted), `aluminium_anodized_black`, `stainless_steel` (satin), `stainless_polished`, `stainless_bead_blasted`, `steel_galvanized`, `steel_black_oxide`, `chrome`, `copper`, `brass`, `ferrite_magnet` (nickel plated) |
| Plastics | `abs`, `pla`, `petg` (with FDM layer lines), `polycarbonate`, `acrylic`, `nylon`, `pom_black`, `rubber`, `pcb_green`, `wood_walnut` |
| Coatings | `powder_matte`, `powder_satin`, `powder_gloss` (set `color`) |
| Transparent | `glass_clear`, `glass_frosted`, `polycarbonate_clear`, `acrylic_clear`, `acrylic_frosted`, `plastic_translucent`, `xray_housing` (alpha blend, no refraction, for technical views) |
| Finishes | `matte`, `satin`, `gloss`, `bead_blasted`, `brushed`, `polished`, `textured`, `machined` |

## Surface detail

The `bump` types are `noise`, `orange_peel` (coatings and moulded parts), `brushed` (anisotropic streaks along
`radial_z` for turned parts or `linear_x` for flat stock), `layer_lines` (FDM, 0.2 mm in Z) and `none`. The sizes are
real, in mm, because the scene is in metres. `variation` adds low-frequency roughness noise so large faces are not
perfectly uniform. Keep it subtle: the light should do the work, not the textures.

## Tips

- Metal looks flat when it has nothing to reflect. Lower the world strength or use a rig with strip lights, rather than lowering roughness on everything.
- Clear parts need closed meshes. STEP solids always are. Transmission makes renders slower and noisier, so give clear parts more samples if needed.
- Black parts: never pure black. Use a value of about `#1A1A1C` and roughness 0.3 to 0.5, so their form still shows.
