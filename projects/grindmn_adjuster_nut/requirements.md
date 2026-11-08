# grindmn adjuster nut: Part 12, 6061-T6, diamond knurl, clear anodise, thread masked

Grind dial: M8 x 0.75 nut on the shaft's top thread, 0-44 scale etched on the top chamfer, push-fit ball plunger at r 12 clicking into the disc.

Values are **given** in `projects/grindmn/requirements.md` (top-adjust layout, 2026-11-08) unless they depend on the burr set (**assumed** there). Driving values: `parameters/params.json`, written by `projects/grindmn/gen_projects.py`. Geometry and the hand-worked volume: `projects/grindmn/grindmn_parts.py`. z = 0 at the part's own bottom face, z up, axis on the origin.

Expected: volume 6530.095 mm³, bounding box 30.0 × 30.0 × 10.0 mm.

Left out on purpose: thread form (threads at nominal or tap-drill diameter), knurls, 0.3 edge chamfers, etching; click grooves are modelled square.
