"""Assemble a render STEP of the approved round-12 deck: the built shell and back plate (with their openings),
the Pi 4 + DAC Pro and the 5in screen split by material, and the round-9 massing bodies of everything else
(encoders, knob caps, feet, screws, nuts). Run with FreeCADCmd."""
import os
import FreeCAD as App, Part, Import

HERE = os.path.dirname(os.path.abspath(__file__))
PROD = os.path.dirname(HERE)
MASS = os.path.join(PROD, "draft", "round_12", "A", "massing", "massing.step")
V = App.Vector
# sheet parts are built flat-root; stand them up: sheet (x, y, z) -> (x, z, -y), then move into place
PARTS = {"shell": ((0.5, 0.0, 88.0), os.path.join(PROD, "parts", "shell", "folded", "shell.step")),
         "back": ((1.3, 99.5, 87.2), os.path.join(PROD, "parts", "back", "folded", "back.step"))}
SKIP = ("logo", "shell", "back", "pi4", "dac", "screen", "jumpers", "pad")

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
    out.addObject("Part::Feature", name).Shape = s

def box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
# Pi 4 and DAC Pro (round-9 parameters: USB/Ethernet end toward -x, sockets to the back)
px0, px1, py0, py1, zp, zpt, zh, zht = 149.5, 234.5, 33.5, 89.5, 4.0, 5.4, 14.4, 16.0
eth_y, usb3_y, usb2_y = py1 - 45.75, py1 - 27, py1 - 9
# Waveshare 5in DSI: lens 120.7 x 77.2 x 5.4 at x 6, centred in height; VA 109 x 65.8 (5.85 left, 3.1 top)
lx0, lz0 = 6.0, (88.5 - 77.2) / 2
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
    ("screen_board", box(lx0 - 0.15, 6.4, (88.5 - 76) / 2, lx0 + 120.85, 14.0, (88.5 + 76) / 2)),
]
# flacmn logo (round 12): the owner's SVG fill plus its 0.18 stroke on "flac", 40 wide, 8 from the right and bottom
import importSVG
ldoc = App.newDocument("logo")
importSVG.insert(os.path.join(PROD, "references", "flacmn-charcoal.svg"), ldoc.Name)
edges = [e for o in ldoc.Objects if hasattr(o, "Shape") for e in o.Shape.Edges]
face = Part.makeFace([w for w in (Part.Wire(x) for x in Part.sortEdges(edges)) if w.isClosed()], "Part::FaceMakerBullseye")
face = Part.Compound([f.makeOffset2D(0.09, join=0) if f.BoundBox.XMax < 13.5 else f for f in face.Faces])
App.closeDocument(ldoc.Name)
bb = face.BoundBox
m = App.Matrix(); m.move(V(-bb.XMax, -bb.YMin, 0)); face = face.transformGeometry(m)
face.scale(40.0 / bb.XLength)
face.rotate(V(0, 0, 0), V(1, 0, 0), 90)
face.translate(V(241.0 - 8.0, 0, 8.0))
objs.append(("logo", Part.Compound([f.extrude(V(0, -0.05, 0)) for f in face.Faces])))
for label, s in objs:
    out.addObject("Part::Feature", label).Shape = s
dst = os.path.join(HERE, "deck.step")
Import.export(out.Objects, dst)
bb = None
for o in out.Objects:
    bb = o.Shape.BoundBox if bb is None else bb.united(o.Shape.BoundBox)
    print(o.Label, [round(v, 1) for v in (o.Shape.BoundBox.XMin, o.Shape.BoundBox.YMin, o.Shape.BoundBox.ZMin, o.Shape.BoundBox.XMax, o.Shape.BoundBox.YMax, o.Shape.BoundBox.ZMax)])
print("BBOX", round(bb.XLength, 2), round(bb.YLength, 2), round(bb.ZLength, 2))
App.closeDocument(doc.Name); App.closeDocument(out.Name)
