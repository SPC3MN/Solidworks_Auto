# Sleeve (example_pi_zero_case, option A)

Backend: FreeCAD. EXAMPLE part: it shows a product part built from an approved draft. Driving values come from
`parameters/params.json`, written by `design_cli.py params` from `draft/approved/`; the gate refuses the part if one differs.

Axes: x along the board, the open end at +x; y across, ports at −y; z up from the underside.

## Expected values (by hand)

| Item | Arithmetic | mm³ |
|---|---|---|
| Body | 66.9 × 33.8 × 8.7 | 19 672.61 |
| Cavity above the ledges | 65.3 × 30.6 × 4.5 | −8 991.81 |
| Channel between the ledges | 65.3 × 28.2 × 1.0 | −1 841.46 |
| Port slot in the −y wall | (32.65 + 26.5) × 1.6 × 3.5 | −331.24 |
| **Total** | | **8 508.10** |

Bounding box 66.9 × 33.8 × 8.7.
