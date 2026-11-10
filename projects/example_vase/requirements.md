# example_vase: kernel probe for a freeform part (smooth loft, checked by sections)

Backend: FreeCAD. A vase about Z through four circles: Ø40 at z = 0, Ø24 at z = 30 (the waist), Ø36 at z = 60
(the shoulder), Ø30 at z = 80 (the rim). The skin is a smooth surface through them, so **there is no hand volume**:
`spec.json` has no `volume` and checks sections instead. All values **chosen**.

The inside is a second smooth loft through Ø19 at z = 30 and Ø31 at z = 60 (2.5 wall at those stations), starting
at the 3 mm floor.

| Station | Outside | Area |
|---|---|---|
| waist, z = 30 | Ø24 (± 0.05) | π (12² − 9.5²) = 168.861 |
| shoulder, z = 60 | Ø36 (± 0.05) | π (18² − 15.5²) = 263.108 |

Between stations the size is whatever the smooth skin gives; it is not specified and not checked. Where a size
matters, put a station there.

Bounding box 40 × 40 × 80, which holds only if the skin does not bulge past the Ø40 foot between stations: the
pipeline's bbox check is what proves that.
