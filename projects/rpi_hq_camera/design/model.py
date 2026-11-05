"""Raspberry Pi HQ Camera (CS mount), electronics only: no tripod bracket.

Axes: x/y across the 38 x 38 board, origin at a board corner, z up from the
board bottom, with the lens axis at the board centre. Rings are drawn as one
sketch with an outer and an inner contour, so they never overlap the sensor
underneath (no cut needed).
"""
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from swlib import Part, circle, polygon, rect  # noqa: E402


def knurl(cx, cy, r_out, r_root, teeth):
    pts = []
    for i in range(2 * teeth):
        a = math.pi * i / teeth
        r = r_out if i % 2 == 0 else r_root
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def poly_area(pts):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2


def geometry(p):
    """Every primitive as (name, op, profiles, z0, h, volume); used by both the build and expected()."""
    L, T, c = p["pcb"], p["pcb_t"], p["pcb"] / 2
    disc = lambda d: math.pi * d * d / 4  # noqa: E731
    i = p["hole_inset"]
    holes = [(x, y) for x in (i, L - i) for y in (i, L - i)]
    kn = knurl(c, c, p["lock_od"] / 2, p["lock_od"] / 2 - p["knurl_depth"], p["knurl_teeth"])
    z_lock = T + p["base_h"]
    z_tube = z_lock + p["lock_h"]
    ffc = p["ffc"]
    return [
        ("PCB", "add", [rect(c, c, L, L, p["pcb_r"])], 0, T, L * L * T - (4 - math.pi) * p["pcb_r"] ** 2 * T),
        ("Sensor", "add", [rect(c, c, p["sensor"], p["sensor"])], T, p["sensor_h"], p["sensor"] ** 2 * p["sensor_h"]),
        ("Sensor_glass", "add", [rect(c, c, p["glass_l"], p["glass_w"])], T + p["sensor_h"], p["glass_h"],
         p["glass_l"] * p["glass_w"] * p["glass_h"]),
        ("Mount_base", "add", [circle(c, c, p["base_od"]), circle(c, c, p["bore"])], T, p["base_h"],
         (disc(p["base_od"]) - disc(p["bore"])) * p["base_h"]),
        ("Lock_ring", "add", [polygon(kn), circle(c, c, p["bore"])], z_lock, p["lock_h"],
         (poly_area(kn) - disc(p["bore"])) * p["lock_h"]),
        ("CS_tube", "add", [circle(c, c, p["tube_od"]), circle(c, c, p["bore"])], z_tube, p["tube_h"],
         (disc(p["tube_od"]) - disc(p["bore"])) * p["tube_h"]),
        ("FFC_connector", "add_under", [rect(c, ffc["y"], ffc["l"], ffc["w"])], 0, ffc["h"],
         ffc["l"] * ffc["w"] * ffc["h"]),
        ("Holes", "cut", [circle(x, y, p["hole_d"]) for x, y in holes], T, T, -len(holes) * disc(p["hole_d"]) * T),
    ]


def expected(p):
    vol = sum(g[5] for g in geometry(p))
    z_top = p["pcb_t"] + p["base_h"] + p["lock_h"] + p["tube_h"]
    return round(vol, 3), [p["pcb"], p["pcb"], round(z_top + p["ffc"]["h"], 3)]


def build(app, p):
    part = Part(app)
    try:
        for name, op, profs, z0, h, _ in geometry(p):
            if op == "add":
                part.extrude(name, profs, h, z=z0)
            elif op == "add_under":
                part.extrude(name, profs, h, z=z0, down=True)
            else:
                part.cut(name, profs, depth=h, z=z0, down=True)
        part.link({"pcb_t": p["pcb_t"]}, {"D1@PCB": "pcb_t"})
    finally:
        part.close_prefs()
    return part.doc


if __name__ == "__main__":
    prm = json.loads((pathlib.Path(__file__).parents[1] / "parameters" / "params.json").read_text())
    print(expected(prm))
