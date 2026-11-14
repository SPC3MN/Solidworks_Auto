"""Quick mockup (not a /design round): one U piece is the front and both sides, bent round R10 at the front
corners and again at the back corners (one column of rounded slots per bend); flat back, top and bottom plates.
The top and bottom plates screw down at the centre of each corner bend, into tabs folded in from the side walls
and reaching to the bend centre; the back plate screws to tabs on the back bends. Flush countersunk M3. FreeCADCmd."""
import os, math
import FreeCAD as App, Part, Import
V = App.Vector
HERE = "/home/alec/.cache/flacmn_mockup/frame"
W, D, H, t, R = 241.0, 100.5, 88.5, 1.0, 10.0

def box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))

def quarter(cx, cy, a0):
    """R10 bend (outer R, t thick, full height) from angle a0 to a0 + 90 about (cx, cy)."""
    s = Part.makeCylinder(R, H, V(cx, cy, 0), V(0, 0, 1), 90).cut(Part.makeCylinder(R - t, H, V(cx, cy, 0), V(0, 0, 1), 90))
    s.rotate(V(cx, cy, 0), V(0, 0, 1), a0)
    return s

def slot_column(cx, cy, a_mid):
    """One column of rounded slots through the bend at its middle angle."""
    sw, sl, pitch = 1.6, 12.0, 16.0
    n = int((H - 8) // pitch)
    z0 = (H - (n - 1) * pitch - sl) / 2
    ux, uy = math.cos(math.radians(a_mid)), math.sin(math.radians(a_mid))
    cuts = []
    for k in range(n):
        zb = z0 + k * pitch
        s = box(-sw / 2, -2.5, zb + sw / 2, sw / 2, 2.5, zb + sl - sw / 2)
        for zc in (zb + sw / 2, zb + sl - sw / 2):
            s = s.fuse(Part.makeCylinder(sw / 2, 5, V(0, -2.5, zc), V(0, 1, 0)))
        s.translate(V(0, R - t / 2, 0))
        s.rotate(V(0, 0, 0), V(0, 0, 1), a_mid - 90)
        s.translate(V(cx, cy, 0))
        cuts.append(s)
    return Part.makeCompound(cuts)

TB = 3.0                                        # machined acrylic back plate thickness
BASE = 5.0                                      # printed base thickness (under the shell)
BZ = (45.0, H - 7.5)                            # back plate screw heights (clear of the sockets)
screws, nuts = [], []
CORNERS = ((R, R), (W - R, R), (W - R, D - R), (R, D - R))

def upiece():
    """The aluminium U piece: front, sides and four slotted R10 corner bends, no tabs (a printed frame inside
    carries the plates)."""
    s = box(0, R, 0, t, D - R, H).fuse(box(W - t, R, 0, W, D - R, H)).fuse(box(R, 0, 0, W - R, t, H))
    for (cx, cy), a0, mid in zip(CORNERS, (180, 270, 0, 90), (225, 315, 45, 135)):
        s = s.fuse(quarter(cx, cy, a0)).cut(slot_column(cx, cy, mid))
    return s.removeSplitter()

def rrect(x0, y0, x1, y1, r, z0, h):
    b = box(x0 + r, y0, z0, x1 - r, y1, z0 + h).fuse(box(x0, y0 + r, z0, x1, y1 - r, z0 + h))
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        b = b.fuse(Part.makeCylinder(r, h, V(cx, cy, z0)))
    return b.removeSplitter()

def frame():
    """Printed internal frame: four corner posts that fill the inside of the bends (clear of the screen, the Pi's
    USB-C and the cord cut-outs), from the base up to the top plate, with heat-set M3 inserts: one at the top
    and one at the bottom on each bend centre (top plate and base), two in each back post (back plate)."""
    inside = rrect(t + 0.1, t + 0.1, W - t - 0.1, D - t - 0.1, R - t - 0.1, 0, H - t)
    posts = [box(t, t, 0, 12.6, 22, H - t),                                     # front left (screen from x 13)
             box(W - 18, t, 0, W - t, 18, H - t),                               # front right
             box(t, D - 18, 0, 17, D - TB, H - t),                               # back left (cord cut-out from x 18)
             box(228, D - 12, 0, W - t, D - TB, H - t).fuse(box(224, D - 12, 15, W - t, D - TB, H - t))]  # back right: round the USB-C
    f = None
    for p in posts:
        p = p.common(inside)
        f = p if f is None else f.fuse(p)
    holes, inserts = [], []
    for cx, cy in CORNERS:                      # top plate and base screws at the bend centres
        for z0, d in ((H - t - 6, 1), (0.0, 1)):
            holes.append(Part.makeCylinder(2.0, 6, V(cx, cy, z0)))
            inserts.append(Part.makeCylinder(2.3, 4, V(cx, cy, H - t - 4 if z0 > H / 2 else 0.0)).cut(Part.makeCylinder(1.5, 4, V(cx, cy, H - t - 4 if z0 > H / 2 else 0.0))))
            screws.append((cx, cy, H if z0 > H / 2 else -BASE, "z"))
    for xs in (14.0, 227.0):                    # back plate screws into the back posts
        for z in BZ:
            holes.append(Part.makeCylinder(2.0, 6, V(xs, D - TB - 6, z), V(0, 1, 0)))
            inserts.append(Part.makeCylinder(2.3, 4, V(xs, D - TB - 4, z), V(0, 1, 0)).cut(Part.makeCylinder(1.5, 4, V(xs, D - TB - 4, z), V(0, 1, 0))))
            screws.append((xs, D, z, "y"))
    return f.cut(Part.makeCompound(holes)).removeSplitter(), Part.makeCompound(inserts)

shell = upiece()
frm, inserts = frame()


def csk(x, y, z, axis, sgn):
    """Flush countersunk M3 head (Ø6, 90 deg) whose face lies on the plate surface."""
    d = V(0, sgn, 0) if axis == "y" else V(0, 0, sgn)
    p = V(x, y, z) + d * (-0.75 if False else 0) 
    return Part.makeCone(3.0, 1.5, 1.5, V(x, y, z), d)

# plates
def rrect(x0, y0, x1, y1, r, z0, h):
    b = box(x0 + r, y0, z0, x1 - r, y1, z0 + h).fuse(box(x0, y0 + r, z0, x1, y1 - r, z0 + h))
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        b = b.fuse(Part.makeCylinder(r, h, V(cx, cy, z0)))
    return b.removeSplitter()
back = box(R + 0.2, D - TB, 0, W - R - 0.2, D, H)
top = rrect(t + 0.2, t + 0.2, W - t - 0.2, D - t - 0.2, R - t - 0.2, H - t, t)
# 3D-printed base: 5 thick, an inverted trapezoid in section: its top face is the whole deck outline (out to the
# aluminium edges), its underside is inset 5 mm all round (45 deg sides)
def outline(inset, z):
    sl = rrect(inset, inset, W - inset, D - inset, R - inset, z, 1.0)
    return [f for f in sl.Faces if abs(f.BoundBox.ZMax - z) < 1e-6 and abs(f.BoundBox.ZMin - z) < 1e-6][0].OuterWire
bottom = Part.makeLoft([outline(BASE, -BASE), outline(0.0, 0.0)], True, True)
# front openings (screen window, encoders): layout of the wrap mockup
lx0, kb_x, ks_x, kb_z, ks_z = 13.0, 157.5, 211.3, H / 2, 56.9   # screen 2 mm right, clear of the front-left post
va_x0, va_z1 = lx0 + 5.85, (H - 77.2) / 2 + 77.2 - 3.1
shell = shell.cut(box(va_x0 - 0.5, -1, va_z1 - 65.8 - 0.5, va_x0 + 109 + 0.5, 2, va_z1 + 0.5))
for x, z in ((kb_x, kb_z), (ks_x, ks_z)):
    shell = shell.cut(Part.makeCylinder(3.7, 3, V(x, -1, z), V(0, 1, 0)))
# back openings: sockets and cord cut-outs
px1, py1, zht, zpt = 231.5, 88.0, 16.0, 5.4    # Pi + DAC 1.5 mm forward: the RCA barrels stop 0.5 short of the 3 mm back plate
def stad(x, z, l, w):
    r = w / 2
    return box(x - l / 2 + r, D - TB - 1, z - r, x + l / 2 - r, D + 1, z + r).fuse(
        Part.makeCylinder(r, TB + 2, V(x - l / 2 + r, D - TB - 1, z), V(0, 1, 0))).fuse(Part.makeCylinder(r, TB + 2, V(x + l / 2 - r, D - TB - 1, z), V(0, 1, 0)))
for x, z, d in ((px1 - 18.36, zht + 6.5, 13), (px1 - 32.98, zht + 6.5, 13), (px1 - 51.8, zht + 3, 10)):
    back = back.cut(Part.makeCylinder(d / 2, TB + 2, V(x, D - TB - 1, z), V(0, 1, 0)))
back = back.cut(stad(px1 - 11.2, zpt + 1.6, 13, 7.5))
for x, w in ((30, 18), (62, 12), (94, 12)):     # cord cut-outs, centred level with the RCA outlets
    back = back.cut(stad(x, zht + 6.5, 24, w))
# countersinks through the plates and the flush heads
heads = []
for x, y, z, ax in screws:
    if ax == "y":
        sgn = 1 if y < D / 2 else -1
        cs = Part.makeCone(3.0, 1.5, 1.5, V(x, y - sgn * 0.0, z), V(0, sgn, 0)).fuse(Part.makeCylinder(1.7, 4, V(x, y - sgn, z), V(0, sgn, 0)))
        back = back.cut(cs)
        heads.append(Part.makeCone(3.0, 1.5, 1.5, V(x, y, z), V(0, sgn, 0)))
    else:
        sgn = -1 if z > H / 2 else 1
        cs = Part.makeCone(3.0, 1.5, 1.5, V(x, y, z), V(0, 0, sgn)).fuse(Part.makeCylinder(1.7, 8, V(x, y, z - sgn), V(0, 0, sgn)))
        if z > H / 2:
            top = top.cut(cs)
        else:
            bottom = bottom.cut(cs)
        heads.append(Part.makeCone(3.0, 1.5, 1.5, V(x, y, z), V(0, 0, sgn)))

objs = [("shell", shell), ("back_plate", back),
        ("top_plate", top), ("base", bottom),
        ("tab_screws", Part.makeCompound(heads)), ("frame", frm), ("inserts", inserts),
        ("feet", Part.makeCompound([Part.makeCylinder(5, 6, V(x, y, -6 - BASE)) for x in (25, W - 25) for y in (20, D - 20)]))]
# electronics, screen, knobs and logo (as the wrap mockup; the logo moved clear of the right-hand screws)
px0, py0, zp, zh = px1 - 85, py1 - 56, 4.0, 14.4
eth_y, usb3_y, usb2_y = py1 - 45.75, py1 - 27, py1 - 9
objs += [
    ("pi4_pcb", box(px0, py0, zp, px1, py1, zpt)),
    ("pi4_ethernet", box(px0 - 2.7, eth_y - 8, zpt, px0 + 17.4, eth_y + 8, zpt + 13.5)),
    ("pi4_usb", box(px0 - 2.7, usb3_y - 7.25, zpt, px0 + 17.4, usb3_y + 7.25, zpt + 16).fuse(box(px0 - 2.7, usb2_y - 7.25, zpt, px0 + 17.4, usb2_y + 7.25, zpt + 16))),
    ("dac_pcb", box(px1 - 65, py1 - 56.25, zh, px1, py1 + 0.25, zht)),
    ("dac_rca_housing", box(px1 - 39.6, py1 - 14, zht, px1 - 12, py1, zht + 13)),
    ("dac_rca_barrels", Part.makeCylinder(4, 9, V(px1 - 18.36, py1, zht + 6.5), V(0, 1, 0)).fuse(Part.makeCylinder(4, 9, V(px1 - 32.98, py1, zht + 6.5), V(0, 1, 0)))),
    ("screen_glass", box(lx0, 2.0, (H - 77.2) / 2, lx0 + 120.7, 2.6, (H + 77.2) / 2)),
    ("screen_panel", box(lx0, 2.6, (H - 77.2) / 2, lx0 + 120.7, 7.4, (H + 77.2) / 2)),
    ("screen_board", box(lx0 - 0.15, 7.4, (H - 76) / 2, lx0 + 120.85, 15.0, (H + 76) / 2)),
]
def knurl(cx, cz, d, n=180, depth=0.25, h=10.0, gap=1.0, cham=1.0):
    Rk = d / 2
    pts = [V(cx + (Rk if i % 2 == 0 else Rk - depth) * math.cos(math.pi * i / n), 0, cz + (Rk if i % 2 == 0 else Rk - depth) * math.sin(math.pi * i / n)) for i in range(2 * n)]
    f = Part.Face(Part.makePolygon(pts + [pts[0]]))
    f.translate(V(0, -gap - h, 0))
    body = f.extrude(V(0, h, 0))
    env = Part.makeCone(Rk - cham, Rk, cham, V(cx, -gap - h, cz), V(0, 1, 0)).fuse(Part.makeCylinder(Rk, h - cham, V(cx, -gap - h + cham, cz), V(0, 1, 0)))
    return body.common(env)
objs += [("knob_big", knurl(kb_x, kb_z, 57.0)), ("knob_small", Part.makeCylinder(17.5, 10.0, V(ks_x, -11.0, ks_z), V(0, 1, 0)))]
for nm, x, z in (("enc_big", kb_x, kb_z), ("enc_small", ks_x, ks_z)):
    objs.append((nm, box(x - 6.25, 1.0, z - 6.7, x + 6.25, 11.1, z + 6.7).fuse(Part.makeCylinder(3.5, 7, V(x, -6, z), V(0, 1, 0)))))
GRID = ["#.#####..#.##.", "########.#####"] + ["##.##.##.##.##"] * 4
p = 18.0 / 13.9; r = 0.45 * p
x1 = W - R - 4.0
dots = [Part.makeCylinder(r, 0.05, V(x1 - r - (13 - c) * p, -0.05, 8.0 + r + (5 - k) * p), V(0, 1, 0))
        for k, row in enumerate(GRID) for c, ch in enumerate(row) if ch == "#"]
objs.append(("logo", dots[0].fuse(dots[1:])))

out = App.newDocument("frame")
for label, s in objs:
    out.addObject("Part::Feature", label).Shape = s
Import.export(out.Objects, os.path.join(HERE, "deck.step"))
bb = None
for o in out.Objects:
    bb = o.Shape.BoundBox if bb is None else bb.united(o.Shape.BoundBox)
print("SIDES valid", shell.isValid(), "plates", back.isValid(), top.isValid(), bottom.isValid())
print("BBOX", round(bb.XLength, 2), round(bb.YLength, 2), round(bb.ZLength, 2))
# clashes between the structural parts and the electronics (a quick check, not the assembly gate)
names = [n for n, _ in objs]
shapes = dict(objs)
for a in ("shell", "back_plate", "top_plate", "base", "frame"):
    for b in ("pi4_pcb", "pi4_usb", "dac_pcb", "dac_rca_housing", "dac_rca_barrels", "screen_glass", "screen_panel", "screen_board", "enc_big", "enc_small", "logo"):
        v = shapes[a].common(shapes[b]).Volume
        if v > 1e-3:
            print("CLASH", a, b, round(v, 2))
App.closeDocument(out.Name)
