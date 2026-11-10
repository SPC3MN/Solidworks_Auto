# example_loft: kernel probe for `Part.loft` (ruled)

Backend: FreeCAD. A hopper: a 50 × 40 rectangle at z = 0 joined by straight lines to a 30 × 20 rectangle at
z = 30, with a wall 3 thick measured horizontally. All values **chosen**.

A ruled loft between two parallel sections is a prismatoid: V = h/6 (A₀ + 4 A_mid + A₁), the mid section having
the mean sides.

| Item | Arithmetic | mm³ |
|---|---|---|
| Outside | 30/6 (2000 + 4 · 40 · 30 + 600) | 37000.000 |
| Inside | 30/6 (44 · 34 + 4 · 34 · 24 + 24 · 14) | −25480.000 |
| **Total** | | **11520.000** |

Bounding box 50 × 40 × 30. Section at z = 15: 40 × 30 outside, area 40 · 30 − 34 · 24 = 384.
