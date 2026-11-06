# grindmn crank_knob: Crank knob (part 7), 6061-T6

Every value is **given** in `projects/grindmn/requirements.md` (section 5.7) unless it depends on the burr set
(marked **assumed** there). Driving values: `parameters/params.json`. Geometry and the hand-worked volume:
`projects/grindmn/grindmn_parts.py`. z = 0 at the part's own bottom face, z up, axis on the origin.

Expected: volume 8174.424 mm³, bounding box 20.0 × 20.0 × 30.0 mm.

Left out on purpose: thread form (threads at nominal diameter), knurls, 0.3 edge chamfers, lead-ins, etching.
Tapped holes are at tap-drill size (M4 Ø3.3, M3 Ø2.5).
