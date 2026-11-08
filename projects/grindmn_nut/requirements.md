# grindmn nut: Part 5, 6061-T6, diamond knurl, clear anodise, thread masked

Grind nut: M6 x 0.75 with a nylon patch, Ø9 boss on the top bearing's inner ring, 45-line stepless scale on the top chamfer (16.7 µm a line).

Values are **given** in `projects/grindmn/requirements.md` (top-adjust layout, 2026-11-08) unless they depend on the burr set (**assumed** there). Driving values: `parameters/params.json`, written by `projects/grindmn/gen_projects.py`. Geometry and the hand-worked volume: `projects/grindmn/grindmn_parts.py`. z = 0 at the part's own bottom face, z up, axis on the origin.

Expected: volume 4284.642 mm³, bounding box 28.0 × 28.0 × 10.0 mm.

Left out on purpose: thread form (threads at nominal or tap-drill diameter), knurls, 0.3 edge chamfers, etching; click grooves are modelled square.
