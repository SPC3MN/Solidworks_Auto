"""Assemble a render STEP of the approved round-14 deck: the built shell and back plate (with their openings),
the Pi 4 + DAC Pro and the 5in screen split by material, the knurled aluminium and smooth plastic caps, the painted
mn logo, and the round-14 massing bodies of everything else (encoders, feet, screws, nuts). The front face and
everything on it lean back 15 deg about the bottom front edge. Run with FreeCADCmd."""
import os
import FreeCAD as App, Part, Import

HERE = os.path.dirname(os.path.abspath(__file__))
PROD = os.path.dirname(HERE)
MASS = os.path.join(PROD, "draft", "round_14", "A", "massing", "massing.step")
V = App.Vector
# sheet parts are built flat-root; stand them up: sheet (x, y, z) -> (x, z, -y), then move into place
import math
LEAN = 15.0                                   # round 14: the face and its parts lean back about y = z = 0
HF = 88.5 / math.cos(math.radians(LEAN))      # face height in the face frame
PARTS = {"shell": ((0.5, 0.0, HF - 0.5 * math.tan(math.radians((90 - LEAN) / 2))), os.path.join(PROD, "parts", "shell", "folded", "shell.step")),
         "back": ((1.3, 99.5, 87.2), os.path.join(PROD, "parts", "back", "folded", "back.step"))}
SKIP = ("logo", "knob_big", "knob_small", "shell", "back", "pi4", "dac", "screen", "jumpers", "pad")

doc = App.newDocument("deck_render")
Import.insert(MASS, doc.Name)
objs = []
for o in list(doc.Objects):
    if o.TypeId != "Part::Feature" or o.Shape.isNull() or not o.Shape.Solids:
        continue
    if o.Label.split("-")[0] in SKIP or o.Label.startswith("fc_massing"):
        continue
    objs.append((o.Label, o.Shape.copy()))
out = App.newDocument("deck_out")
for name, (off, path) in PARTS.items():
    s = Part.read(path)
    s.rotate(V(0, 0, 0), V(1, 0, 0), -90)
    s.translate(V(*off))
    if name == "shell":
        s.rotate(V(0, 0, 0), V(1, 0, 0), -LEAN)
    out.addObject("Part::Feature", name).Shape = s

def box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
# Pi 4 and DAC Pro (round-9 parameters: USB/Ethernet end toward -x, sockets to the back)
px0, px1, py0, py1, zp, zpt, zh, zht = 149.5, 234.5, 33.5, 89.5, 4.0, 5.4, 14.4, 16.0
eth_y, usb3_y, usb2_y = py1 - 45.75, py1 - 27, py1 - 9
# Waveshare 5in DSI: lens 120.7 x 77.2 x 5.4 at x 6, centred in height; VA 109 x 65.8 (5.85 left, 3.1 top)
lx0, lz0 = 6.0, (HF - 77.2) / 2
objs += [
    ("pi4_pcb", box(px0, py0, zp, px1, py1, zpt)),
    ("pi4_ethernet", box(px0 - 2.7, eth_y - 8, zpt, px0 + 17.4, eth_y + 8, zpt + 13.5)),
    ("pi4_usb", box(px0 - 2.7, usb3_y - 7.25, zpt, px0 + 17.4, usb3_y + 7.25, zpt + 16).fuse(
                box(px0 - 2.7, usb2_y - 7.25, zpt, px0 + 17.4, usb2_y + 7.25, zpt + 16))),
    ("pi4_usbc", box(px1 - 11.2 - 4.5, py1 - 6, zpt, px1 - 11.2 + 4.5, py1 + 1.2, zpt + 3.2)),
    ("dac_pcb", box(px1 - 65, py1 - 56.25, zh, px1, py1 + 0.25, zht)),
    ("dac_rca_housing", box(px1 - 39.6, py1 - 14, zht, px1 - 12, py1, zht + 13)),
    ("dac_rca_barrels", Part.makeCylinder(4, 9, V(px1 - 18.36, py1, zht + 6.5), V(0, 1, 0)).fuse(
                        Part.makeCylinder(4, 9, V(px1 - 32.98, py1, zht + 6.5), V(0, 1, 0)))),
    ("dac_jack", box(px1 - 51.8 - 4, py1 - 12, zht, px1 - 51.8 + 4, py1, zht + 6).fuse(
                 Part.makeCylinder(2.5, 2.5, V(px1 - 51.8, py1, zht + 3), V(0, 1, 0)))),
    ("jumpers", box(px1 - 58, py0 + 1, zht, px1 - 7, py0 + 6, zht + 16.5)),
    ("pad", box(px1 - 29 - 7.5, py1 - 32 - 7.5, 1.0, px1 - 29 + 7.5, py1 - 32 + 7.5, zp)),
    ("screen_glass", box(lx0, 1.0, lz0, lx0 + 120.7, 1.6, lz0 + 77.2)),
    ("screen_panel", box(lx0, 1.6, lz0, lx0 + 120.7, 6.4, lz0 + 77.2)),
    ("screen_board", box(lx0 - 0.15, 6.4, (HF - 76) / 2, lx0 + 120.85, 14.0, (HF + 76) / 2)),
]
import math
# ridged knob caps (round 13): straight ridges round the circumference, 1 mm off the front face, 8 deep
def ridged(cx, cz, d, n, depth=0.6, h=8.0, gap=1.0):
    R = d / 2
    pts = [V(cx + (R if i % 2 == 0 else R - depth) * math.cos(math.pi * i / n), 0, cz + (R if i % 2 == 0 else R - depth) * math.sin(math.pi * i / n)) for i in range(2 * n)]
    f = Part.Face(Part.makePolygon(pts + [pts[0]]))
    f.translate(V(0, -gap - h, 0))
    return f.extrude(V(0, h, 0))
def knurled(cx, cz, d, n=90, rows=4, depth=0.5, cham=1.0, y_front=-9.0, y_back=-1.0):
    """Diamond (criss-cross) knurl: a polyhedral skin of pyramids between valley grid points
    (radius R - depth) and peaks (radius R) on the half-step grid; 45 x 45 degree chamfer on the front edge."""
    R, rv = d / 2, d / 2 - depth
    def pt(r, th, y):
        return V(cx + r * math.cos(th), y, cz + r * math.sin(th))
    y0 = y_front + cham                        # knurl starts behind the chamfer
    a = (y_back - y0) / rows
    th = lambda i: 2 * math.pi * i / n
    vg = [[pt(rv, th(i), y0 + j * a) for j in range(rows + 1)] for i in range(n)]
    faces = []
    tri = lambda p, q, r: faces.append(Part.Face(Part.makePolygon([p, q, r, p])))
    for i in range(n):
        i2 = (i + 1) % n
        for j in range(rows):
            pk = pt(R, th(i + 0.5), y0 + (j + 0.5) * a)
            tri(pk, vg[i][j], vg[i2][j]); tri(pk, vg[i2][j], vg[i2][j + 1])
            tri(pk, vg[i2][j + 1], vg[i][j + 1]); tri(pk, vg[i][j + 1], vg[i][j])
        f0, f1 = pt(R - depth - cham, th(i), y_front), pt(R - depth - cham, th(i + 1), y_front)
        tri(f0, f1, vg[i2][0]); tri(f0, vg[i2][0], vg[i][0])
    front = [pt(R - depth - cham, th(i), y_front) for i in range(n)]
    back = [vg[i][rows] for i in range(n)]
    faces += [Part.Face(Part.makePolygon(front + [front[0]])), Part.Face(Part.makePolygon(back + [back[0]]))]
    return Part.Solid(Part.Shell(faces))

def dimpled(cx, cz, d, h=8.0, gap=1.0, dimple_d=12.0, dimple_depth=1.0, offset=8.5):
    """Smooth cap with a shallow spherical finger dimple on the front face, above the centre."""
    cap = Part.makeCylinder(d / 2, h, V(cx, -gap - h, cz), V(0, 1, 0))
    rs = ((dimple_d / 2) ** 2 + dimple_depth ** 2) / (2 * dimple_depth)
    return cap.cut(Part.makeSphere(rs, V(cx, -gap - h - (rs - dimple_depth), cz + offset)))

def straight_knurl(cx, cz, d, n=180, depth=0.25, h=10.0, gap=1.0, cham=1.0):
    """Fine straight knurl (n grooves, V profile) with a 45 deg chamfer on the front edge."""
    body = ridged(cx, cz, d, n, depth=depth, h=h, gap=gap)
    R, yf = d / 2, -gap - h
    env = Part.makeCone(R - cham, R, cham, V(cx, yf, cz), V(0, 1, 0)).fuse(
          Part.makeCylinder(R, h - cham, V(cx, yf + cham, cz), V(0, 1, 0)))
    return body.common(env)
big = straight_knurl(154.5, HF / 2, 57.0)
print("KNURL valid", big.isValid(), "vol", round(big.Volume, 1))
objs += [("knob_big", big), ("knob_small", Part.makeCylinder(17.5, 10.0, V(208.3, -11.0, 56.9), V(0, 1, 0)))]
# 'mn' dot logo (round 13): 14 x 6 grid, 1.8 pitch, dots 0.9 of the pitch, 8 from the right and bottom edges
GRID = ["#.#####..#.##.", "########.#####"] + ["##.##.##.##.##"] * 4
p = 18.0 / 13.9; r = 0.45 * p      # mn 18 mm wide
dots = [Part.makeCylinder(r, 0.05, V(241.0 - 8.0 - r - (13 - c) * p, -0.05, 8.0 + r + (5 - k) * p), V(0, 1, 0))
        for k, row in enumerate(GRID) for c, ch in enumerate(row) if ch == "#"]
objs.append(("logo", dots[0].fuse(dots[1:])))
for label, s in objs:
    if label.startswith(("screen_", "knob_", "logo")):
        s.rotate(V(0, 0, 0), V(1, 0, 0), -LEAN)
    out.addObject("Part::Feature", label).Shape = s
dst = os.path.join(HERE, "deck.step")
Import.export(out.Objects, dst)
bb = None
for o in out.Objects:
    bb = o.Shape.BoundBox if bb is None else bb.united(o.Shape.BoundBox)
    print(o.Label, [round(v, 1) for v in (o.Shape.BoundBox.XMin, o.Shape.BoundBox.YMin, o.Shape.BoundBox.ZMin, o.Shape.BoundBox.XMax, o.Shape.BoundBox.YMax, o.Shape.BoundBox.ZMax)])
print("BBOX", round(bb.XLength, 2), round(bb.YLength, 2), round(bb.ZLength, 2))
App.closeDocument(doc.Name); App.closeDocument(out.Name)
