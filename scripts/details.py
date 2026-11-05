"""Package-level detail for electronics layouts.

Turns layout entries into feature operations (adds and cuts) together with each
operation's exact volume, so the expected volume can be computed by arithmetic
without SolidWorks. The SolidWorks build is then checked against that sum.

Rules every generator keeps, so that the arithmetic stays exact:
- an add never overlaps existing material (it only touches it at faces);
- a cut always lies entirely inside solid material;
- no sketch edge partly overlaps an existing model edge (SolidWorks rejects
  that; see docs/solidworks_findings.md). Details are inset by at least 0.05 mm.

Op: dict(op="add"|"cut", axis="z"|"y"|"x", at=offset, depth, down, prof, vol)
prof: ("rect", a, b, l, w) | ("circle", a, b, d) | ("poly", [(a, b), ...]) | ("slot", a, b, length, width)
(a, b) are plane coordinates: (x, y) on z planes, (x, z) on y planes, (y, z) on x planes.
"""
import math

from layout_check import part_geom

LEAD_T = 0.1      # lead thickness = body stand-off
CAP_T = 0.05      # passive end-cap thickness


def _area(prof):
    k = prof[0]
    if k == "rect":
        return prof[3] * prof[4]
    if k == "circle":
        return math.pi * (prof[3] / 2) ** 2
    if k == "slot":
        L, W = prof[3], prof[4]
        return (L - W) * W + math.pi * (W / 2) ** 2
    pts = prof[1]
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2


def _op(op, prof, depth, at, axis="z", down=False):
    return {"op": op, "axis": axis, "at": round(at, 6), "depth": depth, "down": down,
            "prof": prof, "vol": _area(prof) * depth}


def _rot(x, y, l, w, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return [(x + px * c - py * s, y + px * s + py * c)
            for px, py in ((-l / 2, -w / 2), (l / 2, -w / 2), (l / 2, w / 2), (-l / 2, w / 2))]


# ---------------------------------------------------------------- generators
# Each takes (x, y, l, w, h, rot, T, c) -> list of ops. l is along x after rotation.

def plain(x, y, l, w, h, rot, T, c):
    prof = ("poly", _rot(x, y, l, w, 45)) if rot == 45 else ("rect", x, y, l, w)
    return [_op("add", prof, h, T)]


def passive(x, y, l, w, h, rot, T, c):
    """Ceramic body with raised metal end caps (on the top face, inset 0.05)."""
    ops = [_op("add", ("rect", x, y, l, w), h - CAP_T, T)]
    along_x = l >= w
    L, Wd = (l, w) if along_x else (w, l)
    cap = 0.25 * L
    for s in (-1, 1):
        cc = s * (L / 2 - 0.05 - cap / 2)
        prof = ("rect", x + cc, y, cap, Wd - 0.1) if along_x else ("rect", x, y + cc, Wd - 0.1, cap)
        ops.append(_op("add", prof, CAP_T, T + h - CAP_T))
    return ops


def gullwing(x, y, l, w, h, rot, T, c, n_side, sides, lead_w, out=0.5, under=0.2):
    """Body lifted LEAD_T on gull-wing leads. sides: 'y' = leads on the two long
    (y-facing) sides, 'x' = on the two x-facing ends."""
    ops = [_op("add", ("rect", x, y, l, w), h - LEAD_T, T + LEAD_T)]
    span = l if sides == "y" else w
    pitch = span / n_side
    for side in (-1, 1):
        for i in range(n_side):
            t = -span / 2 + pitch * (i + 0.5)
            ll = out + under
            if sides == "y":
                cy = y + side * (w / 2 + out / 2 - under / 2)
                ops.append(_op("add", ("rect", x + t, cy, lead_w, ll), LEAD_T, T))
            else:
                cx = x + side * (l / 2 + out / 2 - under / 2)
                ops.append(_op("add", ("rect", cx, y + t, ll, lead_w), LEAD_T, T))
    return ops


def sot23(x, y, l, w, h, rot, T, c):
    """SOT-23: 2 leads on one long side, 1 on the other."""
    vertical = rot == 90                     # long axis along y
    bl, bw = (w, l) if vertical else (l, w)  # body length along its own long axis
    ops = [_op("add", ("rect", x, y, l, w), h - LEAD_T, T + LEAD_T)]
    lw, out, under = 0.4, 0.5, 0.2
    for side, ts in ((-1, (-0.95, 0.95)), (1, (0.0,))):
        for t in ts:
            if vertical:
                ops.append(_op("add", ("rect", x + side * (bw / 2 + out / 2 - under / 2), y + t,
                                       out + under, lw), LEAD_T, T))
            else:
                ops.append(_op("add", ("rect", x + t, y + side * (bw / 2 + out / 2 - under / 2),
                                       lw, out + under), LEAD_T, T))
    return ops


def sod323(x, y, l, w, h, rot, T, c):
    return gullwing(x, y, l, w, h, rot, T, c, 1, "x" if rot != 90 else "y", 0.3, 0.4, 0.15)


def tssop(x, y, l, w, h, rot, T, c):
    return gullwing(x, y, l, w, h, rot, T, c, c.get("pins_side", 14), "y", 0.3, 0.6, 0.2)


def qfn(x, y, l, w, h, rot, T, c):
    """Moulded body on its terminal pads (0.05 stand-off), with a pin-1 dimple.
    Pads run 0.1 under the body and 0.2 beyond it on all four sides."""
    so = 0.05
    ops = [_op("add", ("rect", x, y, l, w), h - so, T + so)]
    ops.append(_op("cut", ("circle", x - l / 2 + 0.7, y + w / 2 - 0.7, 0.5), 0.1, T + h, down=True))
    n = max(2, int(l / 0.65) - 2)
    pitch = l / (n + 2)
    for i in range(n):
        t = -l / 2 + pitch * (i + 1.5)
        for s in (-1, 1):
            ops.append(_op("add", ("rect", x + t, y + s * (w / 2 + 0.05), 0.25, 0.3), so, T))
            ops.append(_op("add", ("rect", x + s * (l / 2 + 0.05), y + t, 0.3, 0.25), so, T))
    return ops


def bga(x, y, l, w, h, rot, T, c):
    """Substrate with a moulded body on top, inset 0.5."""
    sub = 0.3
    return [_op("add", ("rect", x, y, l, w), sub, T),
            _op("add", ("rect", x, y, l - 1.0, w - 1.0), h - sub, T + sub)]


def soc_lid(x, y, l, w, h, rot, T, c):
    """Substrate 1.0 thick with a metal lid inset about 1.2 mm."""
    sub = 1.0
    return [_op("add", ("rect", x, y, l, w), sub, T),
            _op("add", ("rect", x, y, l - 2.4, w - 2.3), h - sub, T + sub)]


def jst(x, y, l, w, h, rot, T, c):
    """White housing with an open socket pocket from the top (0.6 walls, 1.0 floor)."""
    return [_op("add", ("rect", x, y, l, w), h, T),
            _op("cut", ("rect", x, y, l - 1.2, w - 1.2), h - 1.0, T + h, down=True)]


def ffc(x, y, l, w, h, rot, T, c):
    """Ribbon-cable connector with the cable slot along its long axis."""
    slot_l, slot_w = (0.8, w - 2.0) if w > l else (l - 2.0, 0.8)
    return [_op("add", ("rect", x, y, l, w), h, T),
            _op("cut", ("rect", x, y, slot_l, slot_w), h - 0.5, T + h, down=True)]


def usb_a2(x, y, l, w, h, rot, T, c):
    """Stacked dual USB-A, opening at the +x face: two 12.5 x 5.1 ports, 14 deep."""
    front = x + l / 2
    ops = [_op("add", ("rect", x, y, l, w), h, T)]
    for zc in (T + h * 0.27, T + h * 0.73):
        ops.append(_op("cut", ("rect", y, zc, 12.5, 5.1), 14.0, front, axis="x", down=True))
    return ops


def rj45(x, y, l, w, h, rot, T, c):
    front = x + l / 2
    return [_op("add", ("rect", x, y, l, w), h, T),
            _op("cut", ("rect", y, T + 1.5 + 4.25, 11.7, 8.5), 18.0, front, axis="x", down=True)]


def _front_opening(x, y, l, w, h, T, prof):
    """Opening in the -y face, cut from a plane 0.5 mm in front of the back wall."""
    back = y + w / 2 - 0.5
    return [_op("add", ("rect", x, y, l, w), h, T),
            _op("cut", prof, w - 0.5, back, axis="y", down=True)]


def hdmi_micro(x, y, l, w, h, rot, T, c):
    return _front_opening(x, y, l, w, h, T, ("rect", x, T + h / 2, 5.5, 2.0))


def usbc(x, y, l, w, h, rot, T, c):
    return _front_opening(x, y, l, w, h, T, ("slot", x, T + h / 2, 8.3, 2.5))


KINDS = {"plain": plain, "passive": passive, "sot23": sot23, "sod323": sod323,
         "tssop": tssop, "qfn": qfn, "bga": bga, "soc_lid": soc_lid, "jst": jst,
         "ffc": ffc, "usb_a2": usb_a2, "rj45": rj45, "hdmi_micro": hdmi_micro, "usbc": usbc}


def layout_ops(lay, T, detail=True):
    """All ops for a layout's parts (pads handled separately by the caller)."""
    ops = []
    for c in lay["parts"]:
        x, y, l, w, h, rot = part_geom(lay, c)
        kind = c.get("kind") or lay.get("packages", {}).get(c.get("pkg"), {}).get("kind", "plain")
        ops += KINDS[kind if detail else "plain"](x, y, l, w, h, rot, T, c)
    return ops


def total_volume(ops):
    return sum(o["vol"] if o["op"] == "add" else -o["vol"] for o in ops)


def apply(part, ops, prefix, which):
    """Build the ops of one type ('add' or 'cut'), one feature per plane, depth and direction."""
    from swlib import circle, polygon, rect, slot
    makers = {"rect": lambda p: rect(*p[1:]), "circle": lambda p: circle(*p[1:]),
              "poly": lambda p: polygon(p[1]), "slot": lambda p: slot(*p[1:])}
    groups = {}
    for o in ops:
        if o["op"] == which:
            key = (o["axis"], o["at"], round(o["depth"], 6), o["down"])
            groups.setdefault(key, []).append(makers[o["prof"][0]](o["prof"]))
    for n, ((axis, at, depth, down), profs) in enumerate(sorted(groups.items())):
        name = f"{prefix}_{which}{n:02d}"
        if which == "add":
            part.extrude(name, profs, depth, z=at, down=down, axis=axis)
        else:
            part.cut(name, profs, depth=depth, z=at, down=down, axis=axis)
