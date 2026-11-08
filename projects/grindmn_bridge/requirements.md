# grindmn bridge: Part 2, 6061-T6, clear anodise, bearing seat masked

Top bearing carrier: pilot in the hopper bore, flange on the tube's top face, 608 seat bored from the top, three spokes with 9 mm bean openings, dowel hole against rotation.

Values are **given** in `projects/grindmn/requirements.md` (top-adjust layout, 2026-11-08) unless they depend on the burr set (**assumed** there). Driving values: `parameters/params.json`, written by `projects/grindmn/gen_projects.py`. Geometry and the hand-worked volume: `projects/grindmn/grindmn_parts.py`. z = 0 at the part's own bottom face, z up, axis on the origin.

Expected: volume 13285.69 mm³, bounding box 64.0 × 64.0 × 12.0 mm.

Left out on purpose: thread form (threads at nominal or tap-drill diameter), knurls, 0.3 edge chamfers, etching; click grooves are modelled square.
