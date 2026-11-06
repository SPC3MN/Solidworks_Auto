"""Builders for panel hardware: acrylic panel, TS35 DIN rail, DIN-rail screw terminal, and an
enclosed (Mean Well LRS style) power supply mounted on edge. Each has geometry(p) -> list of
(op, ...) with exact volumes, so expected() needs no SolidWorks, and build(app, p) -> doc.

Axes for every part: z up from the mounting surface (the face that sits on the panel).
"""
import math

from swlib import Part, circle, polygon, rect, slot


def poly_area(pts):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2


def disc(d):
    return math.pi * d * d / 4


# ---------------------------------------------------------------- acrylic panel
def panel_expected(p):
    holes = p.get("holes", [])
    v = p["l"] * p["w"] * p["t"] - sum(disc(h["d"]) for h in holes) * p["t"]
    return round(v, 3), [p["l"], p["w"], p["t"]]


def panel_build(app, p):
    part = Part(app)
    try:
        part.extrude("Sheet", [rect(p["l"] / 2, p["w"] / 2, p["l"], p["w"])], p["t"])
        if p.get("holes"):
            part.cut("Holes", [circle(h["x"], h["y"], h["d"]) for h in p["holes"]])
        part.link({"t": p["t"]}, {"D1@Sheet": "t"})
    finally:
        part.close_prefs()
    return part.doc


# ---------------------------------------------------------------- TS35 DIN rail
def rail_profile(p):
    """Top-hat 35 x 7.5, centred on x = 0, base on z = 0 (x, z points)."""
    W, H, t, base = 35.0, p.get("h", 7.5), p.get("t", 1.0), 27.0
    b, f = base / 2, W / 2
    return [(-b, 0), (b, 0), (b, H - t), (f, H - t), (f, H), (b - t, H), (b - t, t), (-(b - t), t),
            (-(b - t), H), (-f, H), (-f, H - t), (-b, H - t)]


def rail_slots(p):
    n = int((p["length"] - p["slot_pitch"] / 2) // p["slot_pitch"])
    return [p["slot_pitch"] / 2 + i * p["slot_pitch"] for i in range(n)
            if p["slot_pitch"] / 2 + i * p["slot_pitch"] + p["slot_l"] / 2 < p["length"]]


def rail_expected(p):
    a = poly_area(rail_profile(p))
    sl, sw = p["slot_l"], p["slot_w"]
    slot_area = (sl - sw) * sw + disc(sw)
    v = a * p["length"] - len(rail_slots(p)) * slot_area * p.get("t", 1.0)
    return round(v, 3), [35.0, p["length"], p.get("h", 7.5)]


def rail_build(app, p):
    part = Part(app)
    try:
        # profile in the (x, z) plane at y = 0, extruded along +y
        part.extrude("Rail", [polygon(rail_profile(p))], p["length"], z=0, axis="y")
        part.cut("Slots", [slot(0, y, p["slot_l"], p["slot_w"], 90) for y in rail_slots(p)])
    finally:
        part.close_prefs()
    return part.doc


# ---------------------------------------------------------------- DIN terminal
def terminal_profile(p):
    """Stepped side profile in (x, z): x across the rail, z up from the rail top."""
    a, b, c = p["w_base"] / 2, p["w_mid"] / 2, p["w_top"] / 2
    z1, z2, z3 = p["z_base"], p["z_mid"], p["h"]
    return [(-a, 0), (a, 0), (a, z1), (b, z1), (b, z2), (c, z2), (c, z3), (-c, z3), (-c, z2),
            (-b, z2), (-b, z1), (-a, z1)]


def terminal_expected(p):
    t = p["pitch"]
    v = poly_area(terminal_profile(p)) * t
    v -= 2 * disc(p["screw_d"]) * p["screw_depth"]
    v -= 2 * p["wire"] * p["wire"] * p["wire_depth"]
    return round(v, 3), [p["w_base"], t, p["h"]]


def terminal_build(app, p):
    part = Part(app)
    t, a = p["pitch"], p["w_base"] / 2
    sx = (p["w_base"] + p["w_mid"]) / 4  # screw pockets centred on the lower steps
    try:
        part.extrude("Body", [polygon(terminal_profile(p))], t, z=0, axis="y")
        part.cut("Screws", [circle(s * sx, t / 2, p["screw_d"]) for s in (-1, 1)],
                 depth=p["screw_depth"], z=p["z_base"], down=True)
        # wire entries in the two end faces (x = +-a), cut inward; Right-plane profiles are (y, z)
        part.cut("Wire_R", [rect(t / 2, p["wire_z"], p["wire"], p["wire"])], depth=p["wire_depth"],
                 z=a, down=True, axis="x")
        part.cut("Wire_L", [rect(t / 2, p["wire_z"], p["wire"], p["wire"])], depth=p["wire_depth"],
                 z=-a, down=False, axis="x")
    finally:
        part.close_prefs()
    return part.doc


# ---------------------------------------------------------------- power supply
def psu_holes(p):
    T, L = p["t"], p["l"]
    xs = [(i - (p["cols"] - 1) / 2) * p["hole_pitch"] for i in range(p["cols"])]
    ys, y = [], p["hole_margin"]
    while y <= L - p["hole_margin"] + 1e-9:
        ys.append(round(y, 4))
        y += p["hole_pitch"]
    return [(x, y) for x in xs for y in ys]


def psu_expected(p):
    L, T, H, w = p["l"], p["t"], p["h"], p["wall"]
    v = L * T * H - (L - 2 * w) * (T - 2 * w) * (H - 2 * w)
    v -= len(psu_holes(p)) * disc(p["hole_d"]) * w
    return round(v, 3), [T, L, H]


def psu_build(app, p):
    """Enclosed supply mounted on edge: footprint t (x) by l (y), standing h out of the panel.
    Sheet-metal box (closed shell, wall thick) with a perforated outward face."""
    L, T, H, w = p["l"], p["t"], p["h"], p["wall"]
    part = Part(app)
    try:
        part.extrude("Case", [rect(0, L / 2, T, L)], H)
        part.shell("Case_shell", w)  # no open faces: a closed, hollow case
        part.cut("Perforation", [circle(x, y, p["hole_d"]) for x, y in psu_holes(p)], depth=w, z=H, down=True)
    finally:
        part.close_prefs()
    return part.doc
