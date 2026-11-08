# grindmn tube: Part 1, 6061-T6, diamond knurl z 22 to 97, clear anodise

Body: spider seat, outer burr seat, hopper and bridge seat bored from the bottom in one chucking; Ø61 spigot and O-ring groove for the flush cup.

Values are **given** in `projects/grindmn/requirements.md` (top-adjust layout, 2026-11-08) unless they depend on the burr set (**assumed** there). Driving values: `parameters/params.json`, written by `projects/grindmn/gen_projects.py`. Geometry and the hand-worked volume: `projects/grindmn/grindmn_parts.py`. z = 0 at the part's own bottom face, z up, axis on the origin.

Expected: volume 105894.297 mm³, bounding box 64.0 × 64.0 × 99.0 mm.

Left out on purpose: thread form (threads at nominal or tap-drill diameter), knurls, 0.3 edge chamfers, etching; click grooves are modelled square.
