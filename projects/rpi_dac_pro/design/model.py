"""Raspberry Pi DAC Pro with all visible components (see requirements.md).

Axes: x along the 65 mm edge, y = 0 at the connector edge, z up from the PCB
bottom. Order: board, then all added components, then all cuts.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import details  # noqa: E402
from layout_check import to_mm  # noqa: E402
from swlib import Part, circle, rect  # noqa: E402


def build(app, p):
    lay = json.loads((pathlib.Path(__file__).parents[1] / "parameters" / "layout.json").read_text())
    part = Part(app)
    try:
        L, W, T = p["pcb_l"], p["pcb_w"], p["pcb_t"]
        pitch, bh, pin, ph = p["hdr_pitch"], p["hdr_block_h"], p["hdr_pin"], p["hdr_pin_h"]
        part.extrude("PCB", [rect(L / 2, W / 2, L, W, p["pcb_r"])], T)

        # J1 (40-pin) and P7 (balanced out) headers
        hy = W - p["hole_inset"]
        n7 = p["p7_n"]
        part.extrude("Header_Blocks", [rect(L / 2, hy, 20 * pitch, 2 * pitch),
                                       rect(p["p7_x"], p["p7_y"], pitch, n7 * pitch)], bh, z=T)
        pins = [rect(L / 2 + (i - 9.5) * pitch, hy + (j - 0.5) * pitch, pin, pin)
                for i in range(20) for j in range(2)]
        pins += [rect(p["p7_x"], p["p7_y"] + (k - (n7 - 1) / 2) * pitch, pin, pin) for k in range(n7)]
        part.extrude("Header_Pins", pins, ph, z=T + bh)

        # Small parts from the photo layout, with package detail (scripts/details.py)
        m = lay["px_to_mm"]
        ops = details.layout_ops(lay, T)
        details.apply(part, ops, "SMD", "add")
        pads = [circle(*to_mm(m, px, py), g["d"]) for g in lay["pads"] for px in g["px"] for py in g["py"]]
        part.extrude("Pads", pads, lay["pad_h"], z=T)

        # RCA block: one housing, front plate past the edge, two barrels
        x0, x1, rh = p["rca_x0"], p["rca_x1"], p["rca_h"]
        cx = (x0 + x1) / 2
        part.extrude("RCA_Housing", [rect(cx, p["rca_d"] / 2, x1 - x0, p["rca_d"])], rh, z=T)
        # Plate is wider than the housing and hangs 0.6 below the board top, so no
        # sketch line partly overlaps a housing edge (SolidWorks rejects that).
        part.extrude("RCA_Plate", [rect(cx, T - 0.6 + rh / 2, x1 - x0 + 2 * p["rca_plate_extra"], rh)],
                     p["rca_plate_t"], z=0, down=True, axis="y")
        az = T + p["rca_axis_h"]
        bxs = (p["rca_bx1"], p["rca_bx2"])
        part.extrude("RCA_Barrels", [circle(x, az, p["rca_barrel_d"]) for x in bxs],
                     p["rca_barrel_out"], z=0, down=True, axis="y")

        # 3.5 mm jack
        jx = p["jack_x"]
        part.extrude("Jack_Body", [rect(jx, p["jack_d"] / 2, p["jack_w"], p["jack_d"])], p["jack_h"], z=T)
        jz = T + p["jack_h"] / 2
        part.extrude("Jack_Nose", [circle(jx, jz, p["jack_nose_d"])], p["jack_nose_out"],
                     z=0, down=True, axis="y")

        # Cuts last
        details.apply(part, ops, "SMD", "cut")
        part.cut("RCA_Bores", [circle(x, az, p["rca_bore_d"]) for x in bxs],
                 depth=p["rca_barrel_out"], z=0, down=True, axis="y")
        part.cut("Jack_Bore", [circle(jx, jz, p["jack_bore_d"])],
                 depth=p["jack_nose_out"], z=0, down=True, axis="y")
        i = p["hole_inset"]
        part.cut("Mount_Holes", [circle(x, y, p["hole_d"]) for x in (i, L - i) for y in (i, W - i)])

        part.link(p, {"D1@PCB": "pcb_t", "D1@RCA_Barrels": "rca_barrel_out"})
    finally:
        part.close_prefs()
    return part.doc
