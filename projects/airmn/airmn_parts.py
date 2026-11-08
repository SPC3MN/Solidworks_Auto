"""airmn prototype: geometry for every part, shared by the build and expected().

Each part is a list of ops (name, op, profiles, z0, h, volume, axis):
  op "add": extrude from the plane at z0 toward +axis by h
  op "cut": cut from the plane at z0 toward +axis by h
  op "pattern": profiles = feature names, z0 = instance count (equal over 360 deg about Z)
Volumes are worked out by hand (closed forms, shoelace areas or 1-D integrals), never read
back from SolidWorks. z = 0 is each part's own bottom face, z up. See ../requirements.md.
"""
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from swlib import Part, circle, polygon, rect  # noqa: E402

PI = math.pi
TAP_M3 = 2.5


def disc(d):
    return PI * d * d / 4


def integ(f, a, b, n=4000):
    """Simpson's rule."""
    h = (b - a) / n
    s = f(a) + f(b) + sum((4 if i % 2 else 2) * f(a + i * h) for i in range(1, n))
    return s * h / 3


def sq(v):
    return math.sqrt(max(v, 0.0))


def poly_area(pts):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2


def rot(pts, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def polar(r, deg):
    return r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg))


def segment_area(r, dist):
    return r * r * math.acos(dist / r) - dist * sq(r * r - dist * dist)


def strip_between(r1, r2, w):
    a = w / 2
    return integ(lambda y: sq(r2 * r2 - y * y) - sq(r1 * r1 - y * y), -a, a)


def spoke(r_in, r_out, w, deg):
    return polygon(rot([(r_in, -w / 2), (r_out, -w / 2), (r_out, w / 2), (r_in, w / 2)], deg))


def ring(d_out, d_in, z0, h, name, op="add"):
    v = (disc(d_out) - disc(d_in)) * h
    return (name, op, [circle(0, 0, d_out), circle(0, 0, d_in)], z0, h, v if op == "add" else -v, "z")


def rod(d, z0, h, name, op="add"):
    v = disc(d) * h
    return (name, op, [circle(0, 0, d)], z0, h, v if op == "add" else -v, "z")


def rabbet(d_part, d_in, z0, h, name):
    """Step cut round the outside edge of a Ø d_part disc down to Ø d_in (sketch circle drawn past the edge)."""
    return (name, "cut", [circle(0, 0, d_part + 2), circle(0, 0, d_in)], z0, h, -(disc(d_part) - disc(d_in)) * h, "z")


def bore_step(d, d_prev, z0, h, name):
    return (name, "cut", [circle(0, 0, d)], z0, h, -(disc(d) - disc(d_prev)) * h, "z")


def holes(name, d, pts, z0, h, op="cut"):
    v = len(pts) * disc(d) * h
    return (name, op, [circle(x, y, d) for x, y in pts], z0, h, -v if op == "cut" else v, "z")


def offset_hole_vol(d, y0, ri, ro):
    """Volume of a Ø d hole along x, its axis at y = y0, through the wall of a tube ri..ro (x > 0 side)."""
    a = d / 2
    return integ(lambda u: 2 * sq(a * a - u * u) * (sq(ro * ro - (y0 + u) ** 2) - sq(ri * ri - (y0 + u) ** 2)),
                 -a, a)


def hexagon(af):
    rv = af / math.sqrt(3)
    return [(rv * math.cos(PI / 3 * i), rv * math.sin(PI / 3 * i)) for i in range(6)]


# ---------------------------------------------------------------------------- pleat geometry

def zigzag(n, ro, ri, flat):
    """Centre line of the pleat pack: n pleats, outer folds at r = ro centred on 0, 360/n, ...,
    inner folds at ri half a pitch later; each fold is a flat `flat` mm long (counter-clockwise)."""
    pts, step = [], 360 / n
    ao, ai = math.degrees(flat / 2 / ro), math.degrees(flat / 2 / ri)
    for k in range(n):
        t = k * step
        pts += [polar(ro, t - ao), polar(ro, t + ao), polar(ri, t + step / 2 - ai), polar(ri, t + step / 2 + ai)]
    return pts


def offset(pts, d):
    """Mitred offset of a closed counter-clockwise polygon, d > 0 outward."""
    n, lines = len(pts), []
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0)
        nx, ny = (y1 - y0) / L, -(x1 - x0) / L
        lines.append(((x0 + nx * d, y0 + ny * d), (x1 - x0, y1 - y0)))
    out = []
    for i in range(n):
        (p, u), (q, v) = lines[i - 1], lines[i]
        den = u[0] * v[1] - u[1] * v[0]
        t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        out.append((p[0] + t * u[0], p[1] + t * u[1]))
    return out


def pleat_band(p, half_w):
    c = zigzag(p["pleats"], p["pleat_ro"], p["pleat_ri"], p["fold_flat"])
    outer, inner = offset(c, half_w), offset(c, -half_w)
    return outer, inner, poly_area(outer) - poly_area(inner)


def box_of(pts):
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    return max(xs) - min(xs), max(ys) - min(ys)


# ---------------------------------------------------------------------------- parts

def rod_pts(p):
    return [polar(p["rod_r"], a) for a in p["rod_angles"]]


def bottom_cap(p):
    D, T = p["d"], p["t"]
    g = [rod(D, 0, T, "Plate"),
         ring(p["groove_od"], p["groove_id"], T - p["groove_depth"], p["groove_depth"], "Comb_groove", "cut"),
         holes("Rod_holes", p["rod_hole"], rod_pts(p), 0, T)]
    nd, nh = p["nut_pocket_d"], p["nut_pocket_depth"]
    g.append(("Nut_pockets", "cut", [circle(x, y, nd) for x, y in rod_pts(p)], 0, nh,
              -len(p["rod_angles"]) * (disc(nd) - disc(p["rod_hole"])) * nh, "z"))
    px, pl, pw, ph = p["pd_pocket"]["x"], p["pd_pocket"]["l"], p["pd_pocket"]["w"], p["pd_pocket"]["h"]
    g.append(("PD_pocket", "cut", [rect(px, 0, pl, pw)], 0, ph, -pl * pw * ph, "z"))
    cx0, cw = p["cable_channel"]["x0"], p["cable_channel"]["w"]
    R, x_end = D / 2, D / 2 + 5
    pocket_end = px + pl / 2
    area = integ(lambda y: sq(R * R - y * y) - pocket_end, -cw / 2, cw / 2)
    g.append(("Cable_channel", "cut", [rect((cx0 + x_end) / 2, 0, x_end - cx0, cw)], 0, ph, -area * ph, "z"))
    return g, [D, D, T]


def comb(p):
    D, Di, T = p["od"], p["id"], p["t"]
    outer, inner, area = pleat_band(p, p["slot_w"] / 2)
    sd = p["slot_depth"]
    g = [ring(D, Di, 0, T, "Ring"),
         ("Pleat_slots", "cut", [polygon(outer), polygon(inner)], T - sd, sd, -area * sd, "z")]
    return g, [D, D, T]


def pleat_pack(p):
    outer, inner, area = pleat_band(p, p["media_t"] / 2)
    H = p["h"]
    bx, by = box_of(outer)
    return [("Pack", "add", [polygon(outer), polygon(inner)], 0, H, area * H, "z")], [bx, by, H]


def gasket(p):
    return [ring(p["od"], p["id"], 0, p["t"], "Gasket")], [p["od"], p["od"], p["t"]]


def inlet_ring(p):
    D, T = p["d"], p["t"]
    g = [ring(D, p["id"], 0, T, "Plate")]
    z = T
    for i, (do, di, h) in enumerate(p["bellmouth_steps"]):
        g.append(ring(do, di, z, h, f"Bellmouth{i + 1}"))
        z += h
    g += [ring(p["groove_od"], p["groove_id"], 0, p["groove_depth"], "Comb_groove", "cut"),
          rabbet(D, p["rabbet_id"], T - p["rabbet_depth"], p["rabbet_depth"], "Band_rabbet"),
          holes("Rod_holes", p["rod_hole"], rod_pts(p), 0, T),
          holes("Spider_screws", TAP_M3, [polar(p["spider_screw_r"], a) for a in p["spider_screw_angles"]], 0,
                p["spider_screw_depth"])]
    return g, [D, D, z]


def band_layout(p):
    """Dot grid: hex pitch p, columns every half pitch round the mid radius; unit = columns A and B."""
    rm = (p["od"] + p["id"]) / 4
    units = p["units"]
    half = 180 / units  # degrees between column A and column B
    yb = rm * math.sin(math.radians(half))
    rows = [p["row_z0"] + i * p["row_pitch"] for i in range(p["rows"])]
    return yb, rows[0::2], rows[1::2]


def outlet_band(p):
    Do, Di, H, d = p["od"], p["id"], p["h"], p["hole_d"]
    ro, ri = Do / 2, Di / 2
    yb, za, zb = band_layout(p)
    va, vb = offset_hole_vol(d, 0, ri, ro), offset_hole_vol(d, yb, ri, ro)
    x0, depth = ro + 0.5, ro - ri + 1.5
    g = [ring(Do, Di, 0, H, "Band"),
         ("Holes_A", "cut", [circle(0, z, d) for z in za], x0 - depth, depth, -len(za) * va, "x"),
         ("Holes_B", "cut", [circle(yb, z, d) for z in zb], x0 - depth, depth, -len(zb) * vb, "x")]
    n = p["units"]
    g.append(("Dot_grid", "pattern", ["Holes_A", "Holes_B"], n, 0, -(n - 1) * (len(za) * va + len(zb) * vb), "z"))
    return g, [Do, Do, H]


def blade_geom(p):
    d = p["rim_r"] * math.sin(math.radians(p["blade_angle"]))
    s0, s1 = sq(p["blade_r0"] ** 2 - d * d), sq(p["rim_r"] ** 2 - d * d)
    return d, s0, s1


def tab_rect(p, grow):
    """Blade tab (grow = 0) or its slot (grow = clearance), along the blade line y = -d."""
    d, s0, s1 = blade_geom(p)
    w = p["tab_w"] / 2 + grow
    a, b = s0 + p["tab_inset0"] - grow, s1 - p["tab_inset1"] + grow
    return [(a, -d - w), (b, -d - w), (b, -d + w), (a, -d + w)]


def blade(p):
    d, s0, s1 = blade_geom(p)
    t, te, tl = p["t"] / 2, p["te"] / 2, p["taper_l"]
    body = [(s0, -d - t), (s1 - tl, -d - t), (s1, -d - te), (s1, -d + te), (s1 - tl, -d + t), (s0, -d + t)]
    tab = tab_rect(p, 0)
    th, H = p["tab_h"], p["h"]
    g = [("Body", "add", [polygon(body)], th, H, poly_area(body) * H, "z"),
         ("Tab_low", "add", [polygon(tab)], 0, th, poly_area(tab) * th, "z"),
         ("Tab_high", "add", [polygon(tab)], th + H, th, poly_area(tab) * th, "z")]
    return g, [s1 - s0, 2 * t, H + 2 * th]


def blade_slots(p, z0, h):
    sl = tab_rect(p, p["slot_clear"])
    n = p["blades"]
    return ("Blade_slots", "cut", [polygon(rot(sl, k * 360 / n)) for k in range(n)], z0, h,
            -n * poly_area(sl) * h, "z")


def shroud(p):
    T = p["t"]
    return [ring(p["od"], p["eye_d"], 0, T, "Shroud"), blade_slots(p, 0, T)], [p["od"], p["od"], T]


def backplate(p):
    T, H = p["t"], p["hub_h"]
    g = [rod(p["od"], 0, T, "Disc"), rod(p["hub_d"], T, H, "Hub"),
         rod(p["bore"], 0, T + H, "Bore", "cut"), blade_slots(p, 0, p["slot_depth"])]
    zc, ri, ro = T + H / 2, p["bore"] / 2, p["hub_d"] / 2
    depth = ro - ri + 1.0
    g.append(("Clamp_screw", "cut", [circle(0, zc, TAP_M3)], ro + 0.5 - depth, depth,
              -offset_hole_vol(TAP_M3, 0, ri, ro), "x"))
    return g, [p["od"], p["od"], T + H]


def bridge(p):
    T, HH = p["t"], p["hub_h"]
    rh, rr, w = p["hub_d"] / 2, p["ring_id"] / 2, p["spoke_w"]
    sp = [spoke(rh - 1, rr + 1, w, a) for a in p["rod_angles"]]
    gp = [polar(p["grommet_r"], a) for a in p["grommet_angles"]]
    g = [ring(p["d"], p["ring_id"], 0, T, "Ring"),
         rod(p["hub_d"], 0, HH, "Hub"),
         ("Spokes", "add", sp, 0, T, len(sp) * strip_between(rh, rr, w) * T, "z"),
         rod(p["bore"], 0, HH, "Bore", "cut"),
         bore_step(p["seat_d"], p["bore"], 0, p["seat_depth"], "Bearing_seat_low"),
         bore_step(p["seat_d"], p["bore"], HH - p["seat_depth"], p["seat_depth"], "Bearing_seat_high"),
         rabbet(p["d"], p["rabbet_id"], 0, p["rabbet_depth"], "Band_rabbet"),
         rabbet(p["d"], p["rabbet_id"], T - p["rabbet_depth"], p["rabbet_depth"], "Cover_rabbet"),
         holes("Rod_holes", p["rod_hole"], rod_pts(p), 0, T),
         holes("Grommet_screws", TAP_M3, gp, HH - p["grommet_screw_depth"], p["grommet_screw_depth"])]
    return g, [p["d"], p["d"], HH]


def hex_grid(pitch, r_max):
    """Hole centres on a hex grid (rows along x, row spacing pitch*sin60) within radius r_max."""
    pts, dy = [], pitch * math.sqrt(3) / 2
    n = int(r_max / dy) + 1
    for j in range(-n, n + 1):
        off = (pitch / 2) * (j % 2)
        m_ = int(r_max / pitch) + 2
        for i in range(-m_, m_ + 1):
            x, y = i * pitch + off, j * dy
            if math.hypot(x, y) <= r_max:
                pts.append((x, y))
    return pts


def impeller_housing(p):
    """Lid round the impeller: solid wall seated in the inlet ring's rabbet, perforated top plate (the outlet,
    vertical), tie rods ending in nut counterbores in the top."""
    D, H, tt = p["d"], p["h"], p["top_t"]
    cb, cd = p["nut_cbore_d"], p["nut_cbore_depth"]
    grid = hex_grid(p["hole_pitch"], p["grid_r"])
    g = [rod(D, 0, H, "Body"), rod(p["id"], 0, H - tt, "Cavity", "cut"),
         holes("Outlet_grid", p["hole_d"], grid, H - tt, tt),
         holes("Rod_holes", p["rod_hole"], rod_pts(p), H - tt, tt),
         ("Nut_counterbores", "cut", [circle(x, y, cb) for x, y in rod_pts(p)], H - cd, cd,
          -len(p["rod_angles"]) * (disc(cb) - disc(p["rod_hole"])) * cd, "z")]
    return g, [D, D, H]


def spider(p):
    """Motor spider under the inlet ring, inside the pack's core: ring screwed up to the inlet ring (its top at
    z = hub_h), 5 spokes, hub with two 608 seats; the motor bracket hangs from the hub's underside on grommets."""
    T, HH = p["t"], p["hub_h"]
    rh, rr, w = p["hub_d"] / 2, p["ring_id"] / 2, p["spoke_w"]
    sp = [spoke(rh - 1, rr + 1, w, a) for a in p["spoke_angles"]]
    sc = [polar(p["screw_r"], a) for a in p["screw_angles"]]
    gp = [polar(p["grommet_r"], a) for a in p["grommet_angles"]]
    z0 = HH - T
    g = [ring(p["od"], p["ring_id"], z0, T, "Ring"),
         rod(p["hub_d"], 0, HH, "Hub"),
         ("Spokes", "add", sp, z0, T, len(sp) * strip_between(rh, rr, w) * T, "z"),
         rod(p["bore"], 0, HH, "Bore", "cut"),
         bore_step(p["seat_d"], p["bore"], 0, p["seat_depth"], "Bearing_seat_low"),
         bore_step(p["seat_d"], p["bore"], HH - p["seat_depth"], p["seat_depth"], "Bearing_seat_high"),
         holes("Ring_screws", p["screw_hole"], sc, z0, T),
         holes("Grommet_screws", TAP_M3, gp, 0, p["grommet_screw_depth"])]
    return g, [p["od"], p["od"], HH]


def lid(p):
    T = p["t"]
    return [ring(p["d"], p["hole_d"], 0, T, "Lid"), holes("Rod_holes", p["rod_hole"], rod_pts(p), 0, T)], \
        [p["d"], p["d"], T]


def motor_pod(p):
    Do, Di, H, tt = p["od"], p["id"], p["h"], p["top_t"]
    ro, ri = Do / 2, Di / 2
    v = offset_hole_vol(p["vent_d"], 0, ri, ro)
    depth = ro - ri + 1.0
    z = p["vent_z"]
    g = [rod(Do, 0, H, "Cup"), rod(Di, 0, H - tt, "Cavity", "cut"),
         ("Vent", "cut", [circle(0, z, p["vent_d"])], ro + 0.5 - depth, depth, -v, "x"),
         ("Vents", "pattern", ["Vent"], p["vents"], 0, -(p["vents"] - 1) * v, "z")]
    return g, [Do, Do, H]


def top_cover(p):
    """Top cover: Ø d tube flush with the band, closed top plate; rods end in counterbores in the top."""
    D, H, tt = p["d"], p["h"], p["top_t"]
    cb, cd = p["nut_cbore_d"], p["nut_cbore_depth"]
    g = [rod(D, 0, H, "Body"), rod(p["id"], 0, H - tt, "Cavity", "cut"),
         holes("Rod_holes", p["rod_hole"], rod_pts(p), H - tt, tt),
         ("Nut_counterbores", "cut", [circle(x, y, cb) for x, y in rod_pts(p)], H - cd, cd,
          -len(p["rod_angles"]) * (disc(cb) - disc(p["rod_hole"])) * cd, "z")]
    return g, [D, D, H]


def motor_bracket(p):
    ft, th, pt = p["flange_t"], p["tube_h"], p["plate_t"]
    zt = ft + th
    fp = [polar(p["grommet_r"], a) for a in p["grommet_angles"]]
    sp = [(-p["motor_screw_pitch"] / 2, 0), (p["motor_screw_pitch"] / 2, 0)]
    g = [ring(p["flange_d"], p["tube_id"], 0, ft, "Flange"),
         ring(p["tube_od"], p["tube_id"], ft, th, "Tube"),
         rod(p["tube_od"], zt, pt, "Plate"),
         rod(p["shaft_hole"], zt, pt, "Shaft_hole", "cut"),
         holes("Motor_screws", p["motor_screw_hole"], sp, zt, pt),
         holes("Grommet_holes", p["grommet_hole"], fp, 0, ft)]
    return g, [p["flange_d"], p["flange_d"], zt + pt]


def motor(p):
    sl, sd, fa = p["shaft_l"], p["shaft_d"], p["flat"]
    g = [rod(sd, 0, sl, "Shaft"), rod(p["d"], sl, p["body_l"], "Body"),
         ("D_flat", "cut", [rect(fa + 1.5, 0, 3, sd + 2)], 0, p["flat_l"],
          -segment_area(sd / 2, fa) * p["flat_l"], "z")]
    return g, [p["d"], p["d"], sl + p["body_l"]]


def coupling(p):
    L = p["l"]
    return [rod(p["d"], 0, L, "Body"), rod(p["bore_low"], 0, p["depth_low"], "Bore_low", "cut"),
            rod(p["bore_high"], L - p["depth_high"], p["depth_high"], "Bore_high", "cut")], [p["d"], p["d"], L]


def plain_rod(p):
    return [rod(p["d"], 0, p["l"], "Rod")], [p["d"], p["d"], p["l"]]


def grommet(p):
    return [ring(p["od"], p["id"], 0, p["h"], "Grommet")], [p["od"], p["od"], p["h"]]


def nut(p):
    hx = hexagon(p["af"])
    return [("Hex", "add", [polygon(hx)], 0, p["t"], poly_area(hx) * p["t"], "z"),
            rod(p["d"], 0, p["t"], "Bore", "cut")], [2 * p["af"] / math.sqrt(3), p["af"], p["t"]]


def pd_board(p):
    L, W, T = p["l"], p["w"], p["t"]
    u = p["usbc"]
    ux = L / 2 + u["overhang"] - u["l"] / 2
    return [("PCB", "add", [rect(0, 0, L, W)], 0, T, L * W * T, "z"),
            ("USB_C", "add", [rect(ux, 0, u["l"], u["w"])], T, u["h"], u["l"] * u["w"] * u["h"], "z")], \
        [L + u["overhang"], W, T + u["h"]]


PARTS = {
    "bottom_cap": bottom_cap, "comb": comb, "pleat_pack": pleat_pack, "gasket": gasket,
    "inlet_ring": inlet_ring, "outlet_band": outlet_band, "blade": blade, "shroud": shroud,
    "backplate": backplate, "bridge": bridge, "top_cover": top_cover, "spider": spider, "impeller_housing": impeller_housing,
    "motor_bracket": motor_bracket, "motor": motor, "coupling": coupling, "rod": plain_rod,
    "grommet": grommet, "nut": nut, "pd_board": pd_board,
}


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
            elif op == "pattern":
                part.circular_pattern(name, profs, int(z0))
            else:
                raise ValueError(op)
    finally:
        part.close_prefs()
    return part.doc
