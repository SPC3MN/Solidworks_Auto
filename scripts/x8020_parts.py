"""Simple, shared 80/20 (15 series) parts used to rebuild existing assemblies at the detail
level of the rest of this repo. Each kind has *_expected(p) -> (volume, bbox) with exact
arithmetic (no SolidWorks needed) and *_build(app, p) -> doc.

Canonical frames (asm_simplify.py maps each source part's own frame onto these):
  profile   cross-section in XY, centred on the origin; extruded along +Z from 0 to length
  bracket   corner at the origin, legs along +X and +Y, width along Z centred on 0
  fastener  axis Z, head from z = 0 to head_h, shank from head_h upward
  plate     corner at the origin, l along X, w along Y, thickness along +Z
  bearing   see bearing_geometry()
"""
import math

from swlib import Part, circle, polygon, rect

CELL = 38.1  # 15 series module (1.5 in)


def poly_area(pts):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2


def disc(d):
    return math.pi * d * d / 4


# ---------------------------------------------------------------- T-slot profile
def profile_outline(p):
    """Outer rectangle nx x ny cells with one straight groove (gw wide, gd deep) centred on
    every 38.1 mm of each face. Counter-clockwise, centred on the origin."""
    nx, ny, gw, gd = p["nx"], p["ny"], p["gw"], p["gd"]
    W, H = nx * CELL, ny * CELL
    x0, y0, x1, y1 = -W / 2, -H / 2, W / 2, H / 2
    pts = [(x0, y0)]
    for i in range(nx):  # bottom, left to right, grooves go +y
        c = x0 + CELL * (i + 0.5)
        pts += [(c - gw / 2, y0), (c - gw / 2, y0 + gd), (c + gw / 2, y0 + gd), (c + gw / 2, y0)]
    pts.append((x1, y0))
    for j in range(ny):  # right, bottom to top, grooves go -x
        c = y0 + CELL * (j + 0.5)
        pts += [(x1, c - gw / 2), (x1 - gd, c - gw / 2), (x1 - gd, c + gw / 2), (x1, c + gw / 2)]
    pts.append((x1, y1))
    for i in reversed(range(nx)):  # top, right to left, grooves go -y
        c = x0 + CELL * (i + 0.5)
        pts += [(c + gw / 2, y1), (c + gw / 2, y1 - gd), (c - gw / 2, y1 - gd), (c - gw / 2, y1)]
    pts.append((x0, y1))
    for j in reversed(range(ny)):  # left, top to bottom, grooves go +x
        c = y0 + CELL * (j + 0.5)
        pts += [(x0, c + gw / 2), (x0 + gd, c + gw / 2), (x0 + gd, c - gw / 2), (x0, c - gw / 2)]
    return pts


def _width_y(p, x):
    """Solid length across Y of the section at a given x (grooves removed)."""
    nx, ny, gw, gd = p["nx"], p["ny"], p["gw"], p["gd"]
    W, H = nx * CELL, ny * CELL
    L = H
    for i in range(nx):  # grooves in the bottom and top faces
        c = -W / 2 + CELL * (i + 0.5)
        if abs(x - c) < gw / 2:
            L -= 2 * gd
    if x < -W / 2 + gd or x > W / 2 - gd:  # grooves in the side faces
        L -= ny * gw
    return L


def _miter_removed(p, tri, n=20000):
    """Volume a through-Y triangular end cut (x, z) removes: integral of height(x) * width(x)."""
    W = p["nx"] * CELL
    x0, x1 = max(min(q[0] for q in tri), -W / 2), min(max(q[0] for q in tri), W / 2)
    tot, dx = 0.0, (x1 - x0) / n
    for k in range(n):
        x = x0 + (k + 0.5) * dx
        zs = []
        for (ax, az), (bx, bz) in zip(tri, tri[1:] + tri[:1]):
            if (ax - x) * (bx - x) <= 0 and ax != bx:
                zs.append(az + (bz - az) * (x - ax) / (bx - ax))
        if len(zs) >= 2:
            h = min(max(zs), p["length"]) - max(min(zs), 0)
            tot += max(h, 0) * _width_y(p, x) * dx
    return tot


def profile_expected(p):
    a = p["nx"] * CELL * p["ny"] * CELL - 2 * (p["nx"] + p["ny"]) * p["gw"] * p["gd"]
    assert abs(a - poly_area(profile_outline(p))) < 1e-6
    v = a * p["length"] - sum(_miter_removed(p, [tuple(q) for q in t]) for t in p.get("miters", []))
    return round(v, 3), [p["nx"] * CELL, p["ny"] * CELL, p["length"]]


def profile_build(app, p):
    part = Part(app)
    try:
        part.extrude("Profile", [polygon(profile_outline(p))], p["length"])
        part.link({"length": p["length"]}, {"D1@Profile": "length"})
        for i, t in enumerate(p.get("miters", [])):  # angled end cuts, triangles in (x, z), through Y
            part.cut(f"Miter{i + 1}", [polygon([tuple(q) for q in t])], None, z=0, axis="y")
    finally:
        part.close_prefs()
    return part.doc


# ---------------------------------------------------------------- corner bracket / gusset
def bracket_outline(p):
    """L section (gusset: plus the triangle between the legs) in XY."""
    a, b, t = p["a"], p["b"], p["t"]
    if p.get("wall"):
        return [(0, 0), (a, 0), (a, t), (t, b), (0, b)]
    return [(0, 0), (a, 0), (a, t), (t, t), (t, b), (0, b)]


def bracket_holes(p):
    """[(leg, s, z)]: leg "x" (hole axis Y, at x = s) or "y" (axis X, at y = s)."""
    out = []
    for leg, length in (("x", p["a"]), ("y", p["b"])):
        s = p["hole_s"]
        while s + p["hole_d"] / 2 < length:
            out += [(leg, s, z) for z in p["hole_z"]]
            s += CELL
    return out


def bracket_expected(p):
    a, b, t, w = p["a"], p["b"], p["t"], p["w"]
    v = poly_area(bracket_outline(p)) * w
    if p.get("wall"):  # pocket between the two side walls
        v -= (a - t) * (b - t) / 2 * (w - 2 * p["wall"])
    v -= len(bracket_holes(p)) * disc(p["hole_d"]) * t
    return round(v, 3), [a, b, w]


def bracket_build(app, p):
    a, b, t, w = p["a"], p["b"], p["t"], p["w"]
    part = Part(app)
    try:
        part.extrude("Body", [polygon(bracket_outline(p))], w, z=-w / 2)
        if p.get("wall"):
            # oversized triangle: only its part inside the body is removed (open on the diagonal)
            tri = [(t, t), (a + 10, t), (t, b + 10)]
            part.cut("Pocket", [polygon(tri)], w - 2 * p["wall"], z=w / 2 - p["wall"])
        holes = bracket_holes(p)
        hx = [circle(s, z, p["hole_d"]) for leg, s, z in holes if leg == "x"]  # (x, z) on Top Plane
        hy = [circle(s, z, p["hole_d"]) for leg, s, z in holes if leg == "y"]  # (y, z) on Right Plane
        if hx:
            part.cut("HolesX", hx, t, z=t, down=True, axis="y")
        if hy:
            part.cut("HolesY", hy, t, z=t, down=True, axis="x")
    finally:
        part.close_prefs()
    return part.doc


# ---------------------------------------------------------------- fastener
def fastener_expected(p):
    v = disc(p["head_d"]) * p["head_h"] + disc(p["shank_d"]) * p["shank_l"]
    d = max(p["head_d"], p["shank_d"])
    return round(v, 3), [d, d, p["head_h"] + p["shank_l"]]


def fastener_build(app, p):
    part = Part(app)
    try:
        part.extrude("Head", [circle(0, 0, p["head_d"])], p["head_h"])
        part.extrude("Shank", [circle(0, 0, p["shank_d"])], p["shank_l"], z=p["head_h"])
    finally:
        part.close_prefs()
    return part.doc


# ---------------------------------------------------------------- plate
def plate_holes(p):
    """[(x, y, d)]: explicit holes plus grids {"d", "x": [...], "y": [...]}, plate coordinates."""
    out = [tuple(h) for h in p.get("holes", [])]
    for g in p.get("hole_grids", []):
        out += [(x, y, g["d"]) for x in g["x"] for y in g["y"]]
    return out


def plate_expected(p):
    v = p["l"] * p["w"] * p["t"] - sum(disc(d) for _, _, d in plate_holes(p)) * p["t"]
    return round(v, 3), [p["l"], p["w"], p["t"]]


def plate_build(app, p):
    part = Part(app)
    try:
        part.extrude("Plate", [rect(p["l"] / 2, p["w"] / 2, p["l"], p["w"])], p["t"])
        if plate_holes(p):
            part.cut("Holes", [circle(x, y, d) for x, y, d in plate_holes(p)])
    finally:
        part.close_prefs()
    return part.doc


# ---------------------------------------------------------------- linear bearing
def bearing_blocks(p):
    """Boxes (x0, y0, z0, x1, y1, z1) of the collapsed bearing; filled in once its shape is known."""
    return p["blocks"]


def bearing_expected(p):
    blocks = bearing_blocks(p)
    v = sum((b[3] - b[0]) * (b[4] - b[1]) * (b[5] - b[2]) for b in blocks)
    lo = [min(b[i] for b in blocks) for i in range(3)]
    hi = [max(b[i + 3] for b in blocks) for i in range(3)]
    return round(v, 3), [round(h - l, 6) for l, h in zip(lo, hi)]


def bearing_build(app, p):
    part = Part(app)
    try:
        for i, b in enumerate(bearing_blocks(p)):
            part.extrude(f"Block{i + 1}", [rect((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, b[3] - b[0], b[4] - b[1])],
                         b[5] - b[2], z=b[2])
    finally:
        part.close_prefs()
    return part.doc
