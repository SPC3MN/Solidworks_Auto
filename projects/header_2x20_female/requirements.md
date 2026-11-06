# 2 × 20 female GPIO socket (HAT underside)

Fills the gap between the Pi's J8 plastic (top at z = 1.6 + 2.5 = 4.1) and the HAT
bottom (z = 1.6 + 11 = 12.6), so it is 8.5 mm tall (**given** by the 11 mm stack
height; the real socket body is about 8.5 mm). 2.54 mm pitch, 50.8 × 5.08 mm
body, centred on J8 at (32.5, 52.5) in Pi coordinates. The socket openings are
1.0 mm square (**estimated**), so the Pi's 0.64 mm pins sit inside them without touching.

## Expected values

- (50.8·5.08 − 40·1.0²)·8.5 = (258.064 − 40)·8.5 = **1853.54 mm³**
- Bounding box 50.8 × 5.08 × 8.5
