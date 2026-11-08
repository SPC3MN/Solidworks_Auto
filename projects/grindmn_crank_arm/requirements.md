# grindmn crank arm: Part 6, 6061-T6, clear anodise

One-piece crank: 8 mm plate on a Ø16 boss, blind D bore resting on the shaft's end (slip fit, nothing holds it), index line on the boss, M6 for the handle at r 85.

Values are **given** in `projects/grindmn/requirements.md` (top-adjust layout, 2026-11-08) unless they depend on the burr set (**assumed** there). Driving values: `parameters/params.json`, written by `projects/grindmn/gen_projects.py`. Geometry and the hand-worked volume: `projects/grindmn/grindmn_parts.py`. z = 0 at the part's own bottom face, z up, axis on the origin.

Expected: volume 11486.6 mm³, bounding box 99.0 × 16.0 × 14.0 mm.

Left out on purpose: thread form (threads at nominal or tap-drill diameter), knurls, 0.3 edge chamfers, etching; click grooves are modelled square.
