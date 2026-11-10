# example_tilted: kernel probe for sketch planes off the model axes

Backend: FreeCAD. A 60 × 40 × 20 block (centred in x and y, z from 0). All values **chosen**.

- A Ø8 hole through the block, its axis 30° off vertical in the x-z plane, entering the top face at x = −10.
  Both elliptical mouths lie wholly on the faces (the lower one is centred at x = −10 − 20 tan 30° = −21.55).
- A Ø10 boss whose axis leaves the top face at x = 15, 20° off vertical the other way, 12 long measured along
  its axis from the face. It is rooted 6 below the face.

| Item | Arithmetic | mm³ |
|---|---|---|
| Block | 60 · 40 · 20 | 48 000.000 |
| Tilted hole | π · 4² · 20 / cos 30° | −1160.832 |
| Boss above the face | π · 5² · 12 (a cylinder cut obliquely holds area × axial length) | +942.478 |
| **Total** | | **47781.646** |

Bounding box 60 × 40 × 32.9864 (z: 20 + 12 cos 20° + 5 sin 20°).
