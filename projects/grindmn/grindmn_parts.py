"""grindmn machined parts: geometry for every part, shared by the build and expected().

Each part is a list of ops (name, op, profiles, z0, h, volume, axis):
  op "add": extrude from the plane at z0 toward +axis by h
  op "cut": cut from the plane at z0 toward +axis by h
  op "fillet": profiles = edge points, h = radius
Volumes are worked out by hand (closed forms or 1-D integrals), never read back from SolidWorks.
z = 0 is each part's own bottom face (see ../requirements.md), z up.

Simplified, on purpose: threads at nominal diameter (shaft: major Ø), no thread form,
no knurl, no 0.3 edge chamfers, no etching. Tapped holes are modelled at their tap-drill size.
"""
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from swlib import Part, circle, polygon, rect  # noqa: E402

PI = math.pi
TAP_M4, TAP_M3 = 3.3, 2.5


def disc(d):
    return PI * d * d / 4


def integ(f, a, b, n=20000):
    """Simpson's rule."""
    h = (b - a) / n
    s = f(a) + f(b) + sum((4 if i % 2 else 2) * f(a + i * h) for i in range(1, n))
    return s * h / 3


def sq(v):
    return math.sqrt(max(v, 0.0))


def radial_hole_vol(d, ri, ro):
    """Volume of a Ø d hole drilled radially through a wall between radii ri and ro."""
    a = d / 2
    return integ(lambda y: 2 * sq(a * a - y * y) * (sq(ro * ro - y * y) - sq(ri * ri - y * y)), -a, a)


def segment_area(r, dist):
    """Area of a circle of radius r beyond a chord at distance dist from the centre."""
    return r * r * math.acos(dist / r) - dist * sq(r * r - dist * dist)


def poly_area(pts):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2


def rot(pts, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def spoke(r_in, r_out, w, deg):
    """Rectangle along the angle deg from r_in to r_out, w wide."""
    return polygon(rot([(r_in, -w / 2), (r_out, -w / 2), (r_out, w / 2), (r_in, w / 2)], deg))


def strip_between(r1, r2, w):
    """Area between circles r1 < r2 inside a strip |y| < w/2 (one side, x > 0)."""
    a = w / 2
    return integ(lambda y: sq(r2 * r2 - y * y) - sq(r1 * r1 - y * y), -a, a)


def ring(d_out, d_in, z0, h, name, op="add"):
    v = (disc(d_out) - disc(d_in)) * h
    return (name, op, [circle(0, 0, d_out), circle(0, 0, d_in)], z0, h, v if op == "add" else -v, "z")


def rod(d, z0, h, name, op="add"):
    v = disc(d) * h
    return (name, op, [circle(0, 0, d)], z0, h, v if op == "add" else -v, "z")


def bore_step(d, d_prev, z0, h, name):
    """Cut a Ø d circle over z0..z0+h where a Ø d_prev bore is already open."""
    return (name, "cut", [circle(0, 0, d)], z0, h, -(disc(d) - disc(d_prev)) * h, "z")


def radial(name, d, z, deg, ri, ro):
    """Radial hole at height z and angle deg (0, 90, 180 or 270) through the wall ri..ro."""
    depth = ro - ri + 1.0
    v = -radial_hole_vol(d, ri, ro)
    if deg == 0:
        return (name, "cut", [circle(0, z, d)], ro + 0.5 - depth, depth, v, "x")
    if deg == 180:
        return (name, "cut", [circle(0, z, d)], -ro - 0.5, depth, v, "x")
    if deg == 90:
        return (name, "cut", [circle(0, z, d)], ro + 0.5 - depth, depth, v, "y")
    return (name, "cut", [circle(0, z, d)], -ro - 0.5, depth, v, "y")


# ---------------------------------------------------------------------------- parts

def tube(p):
    """Top-adjust tube: three bores from the bottom in one chucking (spider seat, burr seat, hopper);
    the bridge sits in the top of the hopper bore with its flange on the top face."""
    L, OD = p["length"], p["od"]
    g = [rod(OD, 0, L, "Body")]
    bores = [  # (d, z_top) cut from z = 0 upward, widest-reaching first
        ("Hopper", p["hopper_d"], L), ("Burr_seat", p["burr_seat_d"], p["z_burr_shoulder"]),
        ("Spider_seat", p["spider_seat_d"], p["z_spider_top"]),
    ]
    prev = 0.0
    for name, d, ztop in bores:
        g.append((name, "cut", [circle(0, 0, d)], 0, ztop, -(disc(d) - (disc(prev) if prev else 0)) * ztop, "z"))
        prev = d
    outer = OD
    if p.get("spigot"):  # turned-down bottom for a flush catch cup
        sd, sh = p["spigot"]["d"], p["spigot"]["h"]
        g.append(("Spigot", "cut", [circle(0, 0, OD + 2), circle(0, 0, sd)], 0, sh, -(disc(OD) - disc(sd)) * sh, "z"))
        outer = sd
    gz = p["oring_groove"]
    g.append(("Oring_groove", "cut", [circle(0, 0, outer + 2), circle(0, 0, gz["floor_d"])], gz["z0"], gz["w"],
              -(disc(outer) - disc(gz["floor_d"])) * gz["w"], "z"))
    r = OD / 2
    if p.get("z_burr_screws"):
        g.append(radial("Burr_screw_90", TAP_M4, p["z_burr_screws"], 90, p["burr_seat_d"] / 2, r))
        g.append(radial("Burr_screw_270", TAP_M4, p["z_burr_screws"], 270, p["burr_seat_d"] / 2, r))
    if p.get("dowel"):
        dw = p["dowel"]
        g.append(("Dowel_hole", "cut", [circle(dw["r"], 0, dw["d"])], L - dw["depth"], dw["depth"],
                  -disc(dw["d"]) * dw["depth"], "z"))
    return g, [OD, OD, L]


def bridge(p):
    """Top bearing carrier: pilot ring in the hopper bore, flange on the tube's top face, hub with the
    608 seat bored from the top (the adjuster nut loads it down), three spokes, wide bean openings."""
    t, ph = p["t"], p["pilot_h"]
    g = [
        ring(p["pilot_od"], p["ring_id"], 0, ph, "Pilot_ring"),
        ring(p["flange_od"], p["ring_id"], ph, t - ph, "Flange"),
        ring(p["hub_d"], p["lip_hole_d"], 0, t, "Hub"),
    ]
    rh, rr, w = p["hub_d"] / 2, p["ring_id"] / 2, p["spoke_w"]
    sp = [spoke(rh - 1, rr + 1, w, a) for a in p["spoke_angles"]]
    g.append(("Spokes", "add", sp, 0, t, len(sp) * strip_between(rh, rr, w) * t, "z"))
    g.append(bore_step(p["seat_d"], p["lip_hole_d"], t - p["seat_depth"], p["seat_depth"], "Bearing_seat"))
    if p.get("dowel"):
        dw = p["dowel"]
        g.append(("Dowel_hole", "cut", [circle(dw["r"], 0, dw["d"])], ph, t - ph, -disc(dw["d"]) * (t - ph), "z"))
    return g, [p["flange_od"], p["flange_od"], t]


def spider(p):
    """Lower bearing carrier, pressed into the tube from below against the outer burr: thin ring,
    three spokes, hub with the 608 seat bored from the bottom. Open over the burr exit."""
    hh, rz, rh_ = p["hub_h"], p["ring_z0"], p["ring_h"]
    g = [
        ring(p["hub_d"], p["lip_hole_d"], 0, hh, "Hub"),
        ring(p["ring_od"], p["ring_id"], rz, rh_, "Ring"),
    ]
    rh, rr, w = p["hub_d"] / 2, p["ring_id"] / 2, p["spoke_w"]
    sz0, sz1 = p["spoke_z"]
    sp = [spoke(rh - 1, rr + 1, w, a) for a in p["spoke_angles"]]
    g.append(("Spokes", "add", sp, sz0, sz1 - sz0, len(sp) * strip_between(rh, rr, w) * (sz1 - sz0), "z"))
    g.append(bore_step(p["seat_d"], p["lip_hole_d"], 0, p["seat_depth"], "Bearing_seat"))
    top = max(hh, rz + rh_)
    if p.get("tabs"):  # anti-rotation tabs up into the outer burr's lower-face notches
        t = p["tabs"]
        g.append(("Tabs", "add", [spoke(t["r0"], t["r1"], t["w"], a) for a in t["angles"]], rz + rh_, t["h"],
                  len(t["angles"]) * (t["r1"] - t["r0"]) * t["w"] * t["h"], "z"))
        top = rz + rh_ + t["h"]
    return g, [p["ring_od"], p["ring_od"], top]


def catch_cup(p):
    H, R2 = p["h"], p["corner_r"]
    g = [
        rod(p["od"], 0, H, "Body"),
        rod(p["sleeve_d"], H - p["sleeve_depth"], p["sleeve_depth"], "Sleeve_bore", "cut"),
        rod(p["chamber_d"], p["base"], H - p["sleeve_depth"] - p["base"], "Chamber", "cut"),
    ]
    R = p["chamber_d"] / 2
    v = R2 * R2 * (1 - PI / 4) * 2 * PI * (R - R2 + 2 * R2 / (3 * (4 - PI)))
    g.append(("Base_corner", "fillet", [(0, R / 2, p["base"])], 0, R2, v, "z"))
    return g, [p["od"], p["od"], H]


def stepped_shaft(p):
    """grindmn S shaft: Ø8 lower bearing seat and burr drive (two flats; the inner burr's D bore rests on the
    shoulder where the flats start), Ø6 above (the burr slides on from the top), single crank flat at the top.
    The M6 x 0.75 nut thread is modelled at Ø6."""
    d1, d2, L, zs = p["d_low"], p["d_high"], p["length"], p["z_step"]
    f0 = p["flats_z0"]
    g = [rod(d1, 0, zs, "Low"), rod(d2, zs, L - zs, "High")]
    hf = p["burr_flats"] / 2
    g.append(("Burr_flats", "cut", [rect(hf + 1.5, 0, 3, d1 + 2), rect(-hf - 1.5, 0, 3, d1 + 2)], f0, zs - f0,
              -2 * segment_area(d1 / 2, hf) * (zs - f0), "z"))
    k0, ka = p["crank_flat_z"], p["crank_flat"] - d2 / 2
    g.append(("Crank_flat", "cut", [rect(ka + 1.5, 0, 3, d2 + 2)], k0, L - k0, -segment_area(d2 / 2, ka) * (L - k0), "z"))
    return g, [d1, d1, L]


def nut_s(p):
    """grindmn S nut: knurled body with the stepless scale, a boss that bears on the top bearing's inner ring
    only, M6 x 0.75 tapped through (modelled at tap-drill size; nylon patch not modelled)."""
    bh, h = p["boss_h"], p["h"]
    g = [ring(p["boss_d"], p["tap_d"], 0, bh, "Boss"), ring(p["d"], p["tap_d"], bh, h - bh, "Body")]
    return g, [p["d"], p["d"], h]


def crank_s(p):
    """grindmn S crank: one piece, plate with a boss underneath; blind D bore on the shaft's flat (the crank
    rests on the shaft's end, slip fit, nothing holds it); M6 tapped at the handle end."""
    n = 48
    r1, r2, x2, t, bh = p["w_hub"] / 2, p["w_knob"] / 2, p["knob_x"], p["t"], p["boss_h"]
    pts = [(r1 * math.cos(math.radians(90 + 180 * i / n)), r1 * math.sin(math.radians(90 + 180 * i / n))) for i in range(n + 1)]
    pts += [(x2 + r2 * math.cos(math.radians(-90 + 180 * i / n)), r2 * math.sin(math.radians(-90 + 180 * i / n))) for i in range(n + 1)]
    g = [rod(p["boss_d"], 0, bh, "Boss"), ("Plate", "add", [polygon(pts)], bh, t, poly_area(pts) * t, "z")]
    b, dep = p["bore_d"], p["bore_depth"]
    g.append(rod(b, 0, dep, "Bore", "cut"))
    fa = p["flat"] - b / 2
    g.append(("Bore_flat", "add", [rect(fa + 0.75, 0, 1.5, b + 1)], 0, dep, segment_area(b / 2, fa) * dep, "z"))
    g.append(("Handle_thread", "cut", [circle(x2, 0, p["tap_d"])], bh, t, -disc(p["tap_d"]) * t, "z"))
    return g, [x2 + r2 + r1, 2 * r1, bh + t]


PARTS = {
    "tube": tube, "bridge": bridge, "spider": spider, "stepped_shaft": stepped_shaft, "nut_s": nut_s,
    "crank_s": crank_s, "catch_cup": catch_cup,
}


# ---------------------------------------------------------------------------- bought parts (envelope detail)
def outer_burr(p):
    """48 mm conical outer burr (assumed sizes; Evershine-style ring from the user's photos)."""
    D, H, fh = p["od"], p["h"], p["flange_h"]
    R = D / 2
    g = [rod(D, 0, H, "Ring")]
    a = p["flats"] / 2
    g.append(("Flats", "cut", [rect(0, a + 2, D + 4, 4), rect(0, -a - 2, D + 4, 4)], fh, H - fh,
              -2 * segment_area(R, a) * (H - fh), "z"))
    zt = p["bore_step_z"]
    g.append(rod(p["bore_top"], 0, H, "Bore", "cut"))
    g.append(bore_step(p["bore_low"], p["bore_top"], 0, zt, "Bore_low"))
    rb, ap, n, hw = p["bore_top"] / 2, p["tooth_r"], p["teeth"], p["tooth_hw"]
    x0 = rb - 1.0
    tri = [(ap, 0), (x0, hw * (ap - x0) / (ap - rb)), (x0, -hw * (ap - x0) / (ap - rb))]
    k = hw / (ap - rb)  # half-width per mm from the apex
    def width(x):
        half = k * (ap - x)
        if x >= rb:
            return 2 * half
        return 2 * max(0.0, half - sq(rb * rb - x * x))
    area = integ(width, x0, ap, 4000)
    g.append(("Teeth", "cut", [polygon(rot(tri, i * 360 / n)) for i in range(n)], zt, H - zt,
              -n * area * (H - zt), "z"))
    if p.get("notches"):  # anti-rotation notches in the lower face (assumed: check on the bought burr)
        nt = p["notches"]
        rb_low, x0 = p["bore_low"] / 2, nt["r0"]
        a = integ(lambda y: sq(R * R - y * y) - max(x0, sq(rb_low * rb_low - y * y)), -nt["w"] / 2, nt["w"] / 2, 2000)
        g.append(("Notches", "cut", [spoke(x0, R + 1, nt["w"], ang) for ang in nt["angles"]], 0, nt["h"],
                  -len(nt["angles"]) * a * nt["h"], "z"))
    return g, [D, D, H]

def inner_burr(p):
    """48 mm conical inner burr: stepped cone, 4 flutes, 4-lobe top, 8 mm bore with two flats."""
    g, z = [], 0.0
    steps = p["steps"]  # [[d, h], ...] from the base up
    for i, (d, h) in enumerate(steps):
        g.append(rod(d, z, h, f"Step{i + 1}"))
        z += h
    n = 96
    r0, ra = p["lobe_r"], p["lobe_amp"]
    star = [((r0 + ra * math.cos(4 * 2 * PI * i / n)) * math.cos(2 * PI * i / n),
             (r0 + ra * math.cos(4 * 2 * PI * i / n)) * math.sin(2 * PI * i / n)) for i in range(n)]
    th = p["top_h"]
    g.append(("Lobed_top", "add", [polygon(star)], z, th, poly_area(star) * th, "z"))
    H = z + th
    # flutes over the steps between z_f0 and the lobed top
    f0, fr, fw = p["flute_z0"], p["flute_r"], p["flute_w"]
    vol, zz = 0.0, 0.0
    for d, h in steps:
        lo, hi = max(zz, f0), zz + h
        if hi > lo and d / 2 > fr:
            R = d / 2
            vol += integ(lambda y: sq(R * R - y * y) - fr, -fw / 2, fw / 2, 2000) * (hi - lo)
        zz += h
    fl = [spoke(fr, steps[0][0] / 2 + 2, fw, 45 + 90 * k) for k in range(4)]
    g.append(("Flutes", "cut", fl, f0, z - f0, -4 * vol, "z"))
    b, fa = p["bore"], p["bore_flats"] / 2
    g.append(rod(b, 0, H, "Bore", "cut"))
    g.append(("Bore_flats", "add", [rect(fa + 0.6, 0, 1.2, b + 1), rect(-fa - 0.6, 0, 1.2, b + 1)], 0, H,
              2 * segment_area(b / 2, fa) * H, "z"))
    return g, [steps[0][0], steps[0][0], H]

PARTS.update({"outer_burr": outer_burr, "inner_burr": inner_burr})

# ---------------------------------------------------------------------------- standard hardware
# Catalogue-typical sizes (ISO/DIN nominal); single bodies, no thread form, no internal balls.

def bearing(p):
    """Deep-groove ball bearing as one body: inner and outer ring joined by shields recessed `recess`."""
    d, D, B, rec = p["d"], p["D"], p["B"], p["recess"]
    g = []
    fz, fh = 0.0, 0.0
    if p.get("flange_d"):
        fh = p["flange_t"]
        g.append(ring(p["flange_d"], p["ring_od_in"], 0, fh, "Flange"))
    g.append(ring(D, p["ring_id_out"], fh, B - fh, "Outer_ring"))
    g.append(ring(p["ring_od_in"], d, 0, B, "Inner_ring"))
    g.append(ring(p["ring_id_out"], p["ring_od_in"], rec + fh, B - fh - 2 * rec, "Shields"))
    return g, [p.get("flange_d") or D, p.get("flange_d") or D, B]


def oring(p):
    """O-ring as installed in its groove: a Ø cs round bar swept round a circle (3 arcs of 120°)."""
    R, cs = p["centre_d"] / 2, p["cs"]
    pts = [(R * math.cos(2 * PI * i / 3), R * math.sin(2 * PI * i / 3)) for i in range(4)]
    segs = [["arc", (0, 0), pts[i], pts[i + 1]] for i in range(3)]
    return [("Ring", "sweep", segs, cs / 2, cs, 2 * PI * PI * R * (cs / 2) ** 2, "z")], [2 * R + cs, 2 * R + cs, cs]


def handle(p):
    """Revolving handle as an envelope: threaded stud (at nominal Ø) and the grip."""
    sl, gl = p["stud_l"], p["grip_l"]
    return [rod(p["stud_d"], 0, sl, "Stud"), rod(p["grip_d"], sl, gl, "Grip")], [p["grip_d"], p["grip_d"], sl + gl]


PARTS.update({"handle": handle, "bearing": bearing, "oring": oring})


def expected(kind, p):
    kind = p.get("_kind", kind)
    g, bbox = PARTS[kind](p)
    return round(sum(o[5] for o in g), 3), [round(b, 3) for b in bbox]


def build(app, kind, p):
    kind = p.get("_kind", kind)
    g, _ = PARTS[kind](p)
    part = Part(app)
    try:
        for name, op, profs, z0, h, _, ax in g:
            if op == "add":
                part.extrude(name, profs, h, z=z0, axis=ax)
            elif op == "cut":
                part.cut(name, profs, depth=h, z=z0, down=False, axis=ax)
            elif op == "sweep":
                part.sweep(name, h, profs, at=z0, axis=ax)
            else:
                part.fillet(name, h, profs, kind="FACE")
    finally:
        part.close_prefs()
    return part.doc
