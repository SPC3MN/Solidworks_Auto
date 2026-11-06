"""grindmn machined parts: geometry for every part, shared by the build and expected().

Each part is a list of ops (name, op, profiles, z0, h, volume, axis):
  op "add": extrude from the plane at z0 toward +axis by h
  op "cut": cut from the plane at z0 toward +axis by h
  op "fillet": profiles = edge points, h = radius
Volumes are worked out by hand (closed forms or 1-D integrals), never read back from SolidWorks.
z = 0 is each part's own bottom face (see ../requirements.md), z up.

Simplified, on purpose: threads at nominal diameter (tube: minor Ø, dial: major Ø), no thread form,
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
    L, OD = p["length"], p["od"]
    g = [rod(OD, 0, L, "Body")]
    # bores from the bottom, widest-reaching first (each cut starts at z = 0)
    vol_removed = 0
    bores = [  # (d, z_top) cut from z = 0 upward
        (p["lip_d"], L), (p["bridge_seat_d"], p["z_bridge_shoulder"]), (p["hopper_d"], p["z_hopper_top"]),
        (p["burr_seat_d"], p["z_burr_shoulder"]), (p["pilot_d"], p["z_pilot_top"]),
    ]
    prev = 0.0
    for i, (d, ztop) in enumerate(bores):
        name = ["Lip_bore", "Bridge_seat", "Hopper", "Burr_seat", "Pilot_seat"][i]
        v = (disc(d) - (disc(prev) if prev else 0)) * ztop
        g.append((name, "cut", [circle(0, 0, d)], 0, ztop, -v, "z"))
        prev = d
        vol_removed += v
    # thread minor Ø over 0..10 is wider than the pilot; relief wider again
    g.append(bore_step(p["thread_minor_d"], p["pilot_d"], 0, p["z_thread_top"], "Thread_minor"))
    g.append(bore_step(p["relief_d"], p["pilot_d"], p["z_thread_top"], p["relief_h"], "Thread_relief"))
    gz = p["oring_groove"]
    g.append(ring(OD + 2, gz["floor_d"], gz["z0"], gz["w"], "Oring_groove", "cut"))
    # the ring() volume above assumes the full annulus; correct to the part outside the floor only
    name, op, prof, z0, h, _, ax = g[-1]
    g[-1] = (name, op, prof, z0, h, -(disc(OD) - disc(gz["floor_d"])) * h, ax)
    r = OD / 2
    g.append(radial("Burr_screw_90", TAP_M4, p["z_burr_screws"], 90, p["burr_seat_d"] / 2, r))
    g.append(radial("Burr_screw_270", TAP_M4, p["z_burr_screws"], 270, p["burr_seat_d"] / 2, r))
    g.append(radial("Bridge_screw", TAP_M4, p["z_bridge_screw"], 0, p["bridge_seat_d"] / 2, r))
    g.append(radial("Plunger_hole", p["plunger_d"], p["z_plunger"], 180, p["pilot_d"] / 2, r))
    return g, [OD, OD, L]


def groove_area(R, depth):
    """90Â° V-groove, apex at R - depth: area inside the circle R."""
    a = R - depth
    xm = R + 1.0
    return integ(lambda x: 2 * min(x - a, sq(R * R - x * x)), a, xm)


def dial(p):
    g = [
        rod(p["flange_d"], 0, p["z_thread0"], "Flange"),
        rod(p["thread_d"], p["z_thread0"], p["z_thread1"] - p["z_thread0"], "Thread"),
        rod(p["relief_d"], p["z_thread1"], p["z_pilot0"] - p["z_thread1"], "Relief"),
        rod(p["pilot_d"], p["z_pilot0"], p["h"] - p["z_pilot0"], "Pilot"),
        rod(p["bore_d"], 0, p["h"], "Ring_bore", "cut"),
    ]
    hz0, hh = p["h"] - p["hub_h"], p["hub_h"]
    g.append(ring(p["hub_d"], p["lip_hole_d"], hz0, hh, "Hub"))
    rh, rb, w = p["hub_d"] / 2, p["bore_d"] / 2, p["spoke_w"]
    sp = [spoke(rh - 1, rb + 1, w, a) for a in p["spoke_angles"]]
    g.append(("Spokes", "add", sp, hz0, hh, len(sp) * strip_between(rh, rb, w) * hh, "z"))
    seat_h = p["seat_depth"]
    g.append(ring(p["seat_d"], p["lip_hole_d"], p["h"] - seat_h, seat_h, "Bearing_seat", "cut"))
    # click grooves: 60 V-grooves on the pilot
    R, dep, n = p["pilot_d"] / 2, p["groove_depth"], p["grooves"]
    a, out = R - dep, R + 1.0
    tri = [(a, 0), (out, out - a), (out, -(out - a))]
    profs = [polygon(rot(tri, i * 360 / n)) for i in range(n)]
    gh = p["h"] - p["z_pilot0"]
    g.append(("Click_grooves", "cut", profs, p["z_pilot0"], gh, -n * groove_area(R, dep) * gh, "z"))
    return g, [p["flange_d"], p["flange_d"], p["h"]]


def bridge(p):
    t = p["t"]
    g = [
        ring(p["od"], p["ring_id"], 0, t, "Outer_ring"),
        ring(p["hub_d"], p["lip_hole_d"], 0, t, "Hub"),
    ]
    rh, rr, w = p["hub_d"] / 2, p["ring_id"] / 2, p["spoke_w"]
    sp = [spoke(rh - 1, rr + 1, w, a) for a in p["spoke_angles"]]
    g.append(("Spokes", "add", sp, 0, t, len(sp) * strip_between(rh, rr, w) * t, "z"))
    g.append(bore_step(p["seat_d"], p["lip_hole_d"], 0, p["seat_depth"], "Bearing_seat"))
    # screw groove on the OD: 15Â° arc at 0Â°, 1 deep, 2 wide, centred 4 below the top
    R, dep, arc, gw = p["od"] / 2, p["groove_depth"], p["groove_arc"], p["groove_w"]
    ri, n = R - dep, 24
    inner = [(ri * math.cos(math.radians(-arc / 2 + arc * i / n)), ri * math.sin(math.radians(-arc / 2 + arc * i / n)))
             for i in range(n + 1)]
    ro = R + 1.5
    outer = [(ro * math.cos(math.radians(arc / 2)), ro * math.sin(math.radians(arc / 2))),
             (ro * math.cos(math.radians(-arc / 2)), ro * math.sin(math.radians(-arc / 2)))]
    fan = sum(abs(x0 * y1 - x1 * y0) / 2 for (x0, y0), (x1, y1) in zip(inner, inner[1:]))
    area = PI * R * R * arc / 360 - fan
    gz0 = t - p["groove_from_top"] - gw / 2
    g.append(("Screw_groove", "cut", [polygon(inner + outer)], gz0, gw, -area * gw, "z"))
    return g, [p["od"], p["od"], t]


def shaft(p):
    d, L = p["d"], p["length"]
    c0, c1 = p["collar_z"]
    g = [rod(d, 0, c0, "Lower_seat"), rod(p["collar_d"], c0, c1 - c0, "Collar"), rod(d, c1, L - c1, "Upper")]
    for i, z in enumerate(p["clip_grooves_z"]):
        v = (disc(d) - disc(p["groove_d"])) * p["groove_w"]
        g.append((f"Eclip_groove{i + 1}", "cut", [circle(0, 0, d + 2), circle(0, 0, p["groove_d"])], z,
                  p["groove_w"], -v, "z"))
    f0, f1 = p["burr_drive_z"]
    hf = p["burr_flats"] / 2
    g.append(("Burr_flats", "cut", [rect(hf + 1.5, 0, 3, d + 2), rect(-hf - 1.5, 0, 3, d + 2)], f0, f1 - f0,
              -2 * segment_area(d / 2, hf) * (f1 - f0), "z"))
    k0 = p["crank_flat_z"]
    ka = p["crank_flat"] - d / 2  # flat at x = 7.2 - 4 = 3.2 from the axis
    g.append(("Crank_flat", "cut", [rect(ka + 1.5, 0, 3, d + 2)], k0, L - k0,
              -segment_area(d / 2, ka) * (L - k0), "z"))
    return g, [p["collar_d"], p["collar_d"], L]


def spacer(p):
    return [ring(p["od"], p["id"], 0, p["t"], "Spacer")], [p["od"], p["od"], p["t"]]


def lid(p):
    g = [
        ring(p["spigot_d"], p["hole_d"], 0, p["spigot_h"], "Spigot"),
        ring(p["od"], p["hole_d"], p["spigot_h"], p["t"], "Plate"),
    ]
    return g, [p["od"], p["od"], p["spigot_h"] + p["t"]]


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


def crank_hub(p):
    D, H = p["d"], p["h"]
    g = [rod(D, 0, H, "Body"), rod(p["bore_d"], 0, p["bore_depth"], "Bore", "cut")]
    fa = p["flat"] - p["bore_d"] / 2  # flat at 3.2 from the axis
    r = p["bore_d"] / 2
    g.append(("Bore_flat", "add", [rect(fa + 0.75, 0, 1.5, p["bore_d"] + 1)], 0, p["bore_depth"],
              segment_area(r, fa) * p["bore_depth"], "z"))
    g.append(rod(p["magnet_d"], p["bore_depth"], p["magnet_h"], "Magnet_pocket", "cut"))
    sw, sd = p["slot_w"], p["slot_depth"]
    g.append(("Arm_slot", "cut", [rect(0, 0, D + 4, sw)], H - sd, sd,
              -integ(lambda y: 2 * sq((D / 2) ** 2 - y * y), -sw / 2, sw / 2) * sd, "z"))
    s = p["screw_pitch"] / 2
    g.append(("Arm_screws", "cut", [circle(-s, 0, TAP_M3), circle(s, 0, TAP_M3)], H - sd - p["screw_depth"],
              p["screw_depth"], -2 * disc(TAP_M3) * p["screw_depth"], "z"))
    return g, [D, D, H]


def crank_arm(p):
    n = 48
    r1, r2, x1, x2 = p["w_hub"] / 2, p["w_knob"] / 2, p["hub_end_x"], p["knob_x"]
    pts = [(x1 + r1 * math.cos(math.radians(90 + 180 * i / n)), r1 * math.sin(math.radians(90 + 180 * i / n)))
           for i in range(n + 1)]
    pts += [(x2 + r2 * math.cos(math.radians(-90 + 180 * i / n)), r2 * math.sin(math.radians(-90 + 180 * i / n)))
            for i in range(n + 1)]
    t = p["t"]
    s = p["screw_pitch"] / 2
    g = [
        ("Plate", "add", [polygon(pts)], 0, t, poly_area(pts) * t, "z"),
        ("Hub_screws", "cut", [circle(-s, 0, p["screw_hole"]), circle(s, 0, p["screw_hole"])], 0, t,
         -2 * disc(p["screw_hole"]) * t, "z"),
        ("Knob_thread", "cut", [circle(x2, 0, TAP_M4)], 0, t, -disc(TAP_M4) * t, "z"),
    ]
    return g, [x2 + r2 - (x1 - r1), 2 * r1, t]


def crank_knob(p):
    D, H, fb, fd = p["d"], p["h"], p["flange_bore"], p["flange_depth"]
    g = [
        rod(D, 0, H, "Body"),
        rod(p["through"], 0, H, "Through", "cut"),
        bore_step(fb, p["through"], 0, fd, "Bearing_bore_low"),
        bore_step(fb, p["through"], H - fd, fd, "Bearing_bore_high"),
    ]
    return g, [D, D, H]


PARTS = {
    "tube": tube, "dial": dial, "bridge": bridge, "shaft": shaft, "spacer": spacer, "lid": lid,
    "catch_cup": catch_cup, "crank_hub": crank_hub, "crank_arm": crank_arm, "crank_knob": crank_knob,
}


# ---------------------------------------------------------------------------- bought parts (envelope detail)
def round_edge_vol(R, r):
    """Material removed by a radius-r round on the circular edge of a Ø2R end face."""
    return r * r * (1 - PI / 4) * 2 * PI * (R - r + 2 * r / (3 * (4 - PI)))

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

def spring(p):
    """Generic compression spring at its installed length: flat coils joined by short links."""
    od, w, n, L = p["od"], p["wire"], p["coils"], p["length"]
    idd = od - 2 * w
    pitch = (L - w) / (n - 1)
    g = []
    for i in range(n):
        g.append(ring(od, idd, i * pitch, w, f"Coil{i + 1}"))
    gap = pitch - w
    rm = od / 2 - w / 2
    lw = w - 0.2
    for i in range(n - 1):
        ang = 180 * (i % 2)
        prof = spoke(rm - lw / 2, rm + lw / 2, w - 0.2, ang)
        g.append((f"Link{i + 1}", "add", [prof], i * pitch + w, gap, lw * (w - 0.2) * gap, "z"))
    return g, [od, od, L]

def ball_plunger(p):
    """Push-fit ball plunger, smooth Ø5 sleeve flush with the tube OD, rounded Ø3 nose (the ball)."""
    nd, nh, sd, sl, r = p["nose_d"], p["nose_h"], p["sleeve_d"], p["sleeve_l"], p["nose_round"]
    g = [rod(nd, 0, nh, "Ball"), rod(sd, nh, sl, "Sleeve"),
         ("Ball_round", "fillet", [(0, 0, 0)], 0, r, -round_edge_vol(nd / 2, r), "z")]
    return g, [sd, sd, nh + sl]

PARTS.update({"outer_burr": outer_burr, "inner_burr": inner_burr, "spring": spring, "ball_plunger": ball_plunger})

# ---------------------------------------------------------------------------- standard hardware
# Catalogue-typical sizes (ISO/DIN nominal); single bodies, no thread form, no internal balls.

def hexagon(af):
    rv = af / math.sqrt(3)
    return [(rv * math.cos(PI / 3 * i), rv * math.sin(PI / 3 * i)) for i in range(6)]


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


def eclip(p):
    """DIN 6799 retaining ring as a flat C ring: ring with an opening cut on +x."""
    od, idd, t, w = p["od"], p["id"], p["t"], p["opening"]
    g = [ring(od, idd, 0, t, "Ring"),
         ("Opening", "cut", [rect(od / 4 + 0.5, 0, od / 2 + 1, w)], 0, t,
          -integ(lambda y: sq((od / 2) ** 2 - y * y) - sq((idd / 2) ** 2 - y * y), -w / 2, w / 2, 2000) * t, "z")]
    return g, [od / 2 + sq((od / 2) ** 2 - (w / 2) ** 2), od, t]


def washer(p):
    return [ring(p["od"], p["id"], 0, p["t"], "Washer")], [p["od"], p["od"], p["t"]]


def screw(p):
    """Socket screw, z = 0 at the shank tip, head on top. Button heads get a rounded top edge."""
    L, d, dk, k, af, sd = p["length"], p["d"], p["head_d"], p["head_h"], p["socket"], p["socket_depth"]
    g = []
    if p.get("thread_d"):  # shoulder screw: thread, then the shoulder
        tl = p["thread_l"]
        g.append(rod(p["thread_d"], 0, tl, "Thread"))
        g.append(rod(d, tl, L, "Shoulder"))
        top = tl + L
    else:
        g.append(rod(d, 0, L, "Shank"))
        top = L
    g.append(rod(dk, top, k, "Head"))
    if p.get("button_r"):
        g.append(("Button_round", "fillet", [(0, dk / 4, top + k)], 0, p["button_r"],
                  -round_edge_vol(dk / 2, p["button_r"]), "z"))
    hx = hexagon(af)
    g.append(("Socket", "cut", [polygon(hx)], top + k - sd, sd, -poly_area(hx) * sd, "z"))
    return g, [dk, dk, top + k]


def oring(p):
    """O-ring as installed in its groove: a Ø cs round bar swept round a circle (3 arcs of 120°)."""
    R, cs = p["centre_d"] / 2, p["cs"]
    pts = [(R * math.cos(2 * PI * i / 3), R * math.sin(2 * PI * i / 3)) for i in range(4)]
    segs = [["arc", (0, 0), pts[i], pts[i + 1]] for i in range(3)]
    return [("Ring", "sweep", segs, cs / 2, cs, 2 * PI * PI * R * (cs / 2) ** 2, "z")], [2 * R + cs, 2 * R + cs, cs]


def magnet(p):
    return [rod(p["d"], 0, p["h"], "Magnet")], [p["d"], p["d"], p["h"]]


PARTS.update({"bearing": bearing, "eclip": eclip, "washer": washer, "screw": screw, "oring": oring, "magnet": magnet})


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
