"""Raspberry Pi DAC+ HAT, simplified envelope model (see requirements.md).

Axes: x along the 65 mm edge, y = 0 at the connector edge, z up from the PCB
bottom. Order: board, then all added components, then all cuts.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
import details  # noqa: E402
from swlib import Part, circle, rect  # noqa: E402


def build(app, p):
    part = Part(app)
    try:
        L, W, T = p["pcb_l"], p["pcb_w"], p["pcb_t"]
        part.extrude("PCB", [rect(L / 2, W / 2, L, W, p["pcb_r"])], T)

        # 40-pin header on the hole line along the far edge
        hy, pitch = W - p["hole_inset"], p["hdr_pitch"]
        part.extrude("Header_Block", [rect(L / 2, hy, 20 * pitch, 2 * pitch)], p["hdr_block_h"], z=T)
        pins = [rect(L / 2 + (i - 9.5) * pitch, hy + (j - 0.5) * pitch, p["hdr_pin"], p["hdr_pin"])
                for i in range(20) for j in range(2)]
        part.extrude("Header_Pins", pins, p["hdr_pin_h"], z=T + p["hdr_block_h"])

        # Chips (estimated)
        # All chips and passives from smd_layout.json, with package detail
        # (leads, end caps, pin-1 dimples) from scripts/details.py
        lay = json.loads((pathlib.Path(__file__).parents[1] / "parameters" / "smd_layout.json").read_text())
        ops = details.layout_ops(lay, T)
        details.apply(part, ops, "SMD", "add")
        tp = lay["test_pads"]
        part.extrude("Test_Pads", [circle(tp["x0"] + i * tp["pitch"], tp["y0"] + j * tp["pitch"], tp["d"])
                                   for i in range(tp["cols"]) for j in range(tp["rows"])], tp["h"], z=T)

        # RCA sockets: housing on the board, flange + barrel past the edge (-y)
        xs = (p["rca_x1"], p["rca_x2"])
        rw, rd, rh = p["rca_w"], p["rca_d"], p["rca_h"]
        part.extrude("RCA_Housings", [rect(x, rd / 2, rw, rd) for x in xs], rh, z=T)
        axis_z = T + rh / 2
        # Flange hangs 0.6 mm below the board top: if its edges partly overlapped the
        # housing's top/bottom edges, SolidWorks would reject the sketch (see findings).
        part.extrude("RCA_Flanges", [rect(x, axis_z - 0.6, p["rca_flange_w"], rh) for x in xs],
                     p["rca_flange_t"], z=0, down=True, axis="y")
        part.extrude("RCA_Barrels", [circle(x, axis_z, p["rca_barrel_d"]) for x in xs],
                     p["rca_barrel_out"], z=0, down=True, axis="y")

        # 3.5 mm jack at the corner
        jx = p["jack_x"]
        part.extrude("Jack_Body", [rect(jx, p["jack_d"] / 2, p["jack_w"], p["jack_d"])], p["jack_h"], z=T)
        jz = T + p["jack_h"] / 2
        part.extrude("Jack_Nose", [circle(jx, jz, p["jack_nose_d"])], p["jack_nose_out"],
                     z=0, down=True, axis="y")

        # Cuts last: package details, socket bores, then mounting holes
        details.apply(part, ops, "SMD", "cut")
        part.cut("RCA_Bores", [circle(x, axis_z, p["rca_bore_d"]) for x in xs],
                 depth=p["rca_barrel_out"], z=0, down=True, axis="y")
        part.cut("Jack_Bore", [circle(jx, jz, p["jack_bore_d"])],
                 depth=p["jack_nose_out"], z=0, down=True, axis="y")
        i = p["hole_inset"]
        part.cut("Mount_Holes", [circle(x, y, p["hole_d"]) for x in (i, L - i) for y in (i, W - i)])

        part.link(p, {"D1@PCB": "pcb_t", "D1@RCA_Barrels": "rca_barrel_out"})
    finally:
        part.close_prefs()
    return part.doc
