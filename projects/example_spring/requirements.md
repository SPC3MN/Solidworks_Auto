# example_spring: kernel probe for `Part.helix`

Backend: FreeCAD. A spring about Z: Ø2 wire, coil radius 10 to the wire's centre, pitch 4, five turns (height 20
between the wire-centre ends), ends cut square to the wire. All values **chosen**.

| Item | Arithmetic | |
|---|---|---|
| Wire length | 5 · √((2π · 10)² + 4²) | 314.7952 mm |
| **Volume** | π · 1² · length | **988.958 mm³** |

Bounding box 22 × 22 × 21.9960 (z: 20 + 2 cos α, where the lead angle α has cos α = 2πR / √((2πR)² + p²) = 0.99798).

The STL tolerance is 2 %: at the pipeline's 0.05 mm mesh deflection a Ø2 wire comes out about 1.7 % under.
