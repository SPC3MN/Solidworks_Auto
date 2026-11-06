# grindmn catch_cup: Catch cup (part 9), 6061-T6

Every value is **given** in `projects/grindmn/requirements.md` (section 5.9) unless it depends on the burr set
(marked **assumed** there). Driving values: `parameters/params.json`. Geometry and the hand-worked volume:
`projects/grindmn/grindmn_parts.py`. z = 0 at the part's own bottom face, z up, axis on the origin.

Expected: volume 58692.608 mm³, bounding box 68.0 × 68.0 × 74.0 mm.

Left out on purpose: thread form (threads at nominal diameter), knurls, 0.3 edge chamfers, lead-ins, etching.
Tapped holes are at tap-drill size (M4 Ø3.3, M3 Ø2.5).
