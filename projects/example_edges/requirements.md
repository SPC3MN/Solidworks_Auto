# example_edges: kernel probe for `fclib.edges`, `Part.fillet(select=)` and `Part.chamfer`

Backend: FreeCAD. A 40 × 30 × 10 block: R3 on the four vertical edges, a 1 mm chamfer round the top rim (four
straights and the four corner arcs), a Ø10 hole through the middle, and a 0.5 chamfer on the hole's top mouth.
All values **chosen**.

| Item | Arithmetic | mm³ |
|---|---|---|
| Block | 40 · 30 · 10 | 12 000.000 |
| Corner fillets | 4 · (1 − π/4) · 3² · 10 | −77.257 |
| Top-rim chamfer | straights: 1²/2 · (2 · 34 + 2 · 24) = 58; corners: one full ring 2π (3 − 1/3) · 1²/2 | −66.378 |
| Hole | π · 5² · 10 | −785.398 |
| Hole-mouth chamfer | 2π (5 + 0.5/3) · 0.5²/2 | −4.058 |
| **Total** | | **11066.910** |

Bounding box 40 × 30 × 10. Feature volumes are signed (a cut is negative). The corner fillets are
not in `features`: the rim chamfer depends on them, so replaying without them changes the chamfer too.
