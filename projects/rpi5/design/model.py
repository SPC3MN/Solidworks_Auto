"""Raspberry Pi 5 envelope model (see requirements.md).

Axes: x along the 85 mm edge, y = 0 at the HDMI edge, z up from the PCB bottom.
Order: board, headers, components from layout.json, then the mounting holes.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import details  # noqa: E402
from swlib import Part, circle, rect  # noqa: E402

def build(app, p):
    lay = json.loads((pathlib.Path(__file__).parents[1] / "parameters" / "layout.json").read_text())
    part = Part(app)
    try:
        L, W, T = p["pcb_l"], p["pcb_w"], p["pcb_t"]
        pitch, bh, pin, ph = p["hdr_pitch"], p["hdr_block_h"], p["hdr_pin"], p["hdr_pin_h"]
        part.extrude("PCB", [rect(L / 2, W / 2, L, W, p["pcb_r"])], T)

        # GPIO (2x20) and PoE (2x2) headers
        gx, gy, qx, qy = p["gpio_x"], p["gpio_y"], p["poe_x"], p["poe_y"]
        part.extrude("Header_Blocks", [rect(gx, gy, 20 * pitch, 2 * pitch),
                                       rect(qx, qy, 2 * pitch, 2 * pitch)], bh, z=T)
        pins = [rect(gx + (i - 9.5) * pitch, gy + (j - 0.5) * pitch, pin, pin)
                for i in range(20) for j in range(2)]
        pins += [rect(qx + (i - 0.5) * pitch, qy + (j - 0.5) * pitch, pin, pin)
                 for i in range(2) for j in range(2)]
        part.extrude("Header_Pins", pins, ph, z=T + bh)

        # Components with package/connector detail (scripts/details.py): adds first, cuts last
        ops = details.layout_ops(lay, T)
        details.apply(part, ops, "Parts", "add")
        details.apply(part, ops, "Parts", "cut")

        part.cut("Mount_Holes", [circle(x, y, p["hole_d"])
                                 for x in (p["hole_x1"], p["hole_x2"]) for y in (p["hole_y1"], p["hole_y2"])])
        part.link(p, {"D1@PCB": "pcb_t"})
    finally:
        part.close_prefs()
    return part.doc
