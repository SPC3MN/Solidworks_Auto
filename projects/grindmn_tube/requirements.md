# grindmn tube: Part 1, 6061-T6, diamond knurl above the cup, clear anodise

Body: spider seat, outer burr seat and hopper bored from the bottom in one chucking; O-ring groove for the cup; two M4 burr screws; dowel hole in the top face for the bridge.

Values are **given** in `projects/grindmn/requirements.md` (top-adjust layout, 2026-11-08) unless they depend on the burr set (**assumed** there). Driving values: `parameters/params.json`, written by `projects/grindmn/gen_projects.py`. Geometry and the hand-worked volume: `projects/grindmn/grindmn_parts.py`. z = 0 at the part's own bottom face, z up, axis on the origin.

Expected: volume 111617.366 mm³, bounding box 64.0 × 64.0 × 99.0 mm.

Left out on purpose: thread form (threads at nominal or tap-drill diameter), knurls, 0.3 edge chamfers, etching; click grooves are modelled square.
