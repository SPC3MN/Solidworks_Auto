# grindmn shaft: Part 4, 416 stainless, bearing seats ground

Stepped shaft hung from the nut: Ø8 lower seat and burr drive flats (the burr rests where they start), Ø6 above with the top seat, M6 x 0.75 thread (modelled at Ø6) and the crank flat.

Values are **given** in `projects/grindmn/requirements.md` (top-adjust layout, 2026-11-08) unless they depend on the burr set (**assumed** there). Driving values: `parameters/params.json`, written by `projects/grindmn/gen_projects.py`. Geometry and the hand-worked volume: `projects/grindmn/grindmn_parts.py`. z = 0 at the part's own bottom face, z up, axis on the origin.

Expected: volume 4628.455 mm³, bounding box 8.0 × 8.0 × 134.0 mm.

Left out on purpose: thread form (threads at nominal or tap-drill diameter), knurls, 0.3 edge chamfers, etching; click grooves are modelled square.
