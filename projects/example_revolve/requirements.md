# example_revolve: kernel probe for `Part.revolve`

Backend: FreeCAD. A turned knob about Z: Ø30 × 8 flange, Ø20 stem to z = 25, a 90°-ish V-groove 3 wide and 2 deep
centred at z = 16.5, and a Ø8 bore 15 deep from the top. All values **chosen**.

| Item | Arithmetic | mm³ |
|---|---|---|
| Body | π (15² · 8 + 10² · 17) = 3500 π | 10995.574 |
| V-groove | Pappus: 2π · (10 − 2/3) · (3 · 2 / 2) = 56 π | −175.929 |
| Bore | π · 4² · 15 = 240 π | −753.982 |
| **Total** | 3204 π | **10065.663** |

Bounding box 30 × 30 × 25.
