"""Assemble a render STEP of the approved round-4 deck: the built shell and plate (with their openings)
plus the massing bodies of everything else. Run with FreeCADCmd."""
import os
import FreeCAD as App, Part, Import

HERE = os.path.dirname(os.path.abspath(__file__))
PROD = os.path.dirname(HERE)
MASS = os.path.join(PROD, "draft", "round_4", "A", "massing", "massing.step")
PARTS = {"shell": ((0.5, 0.5, 45.0), os.path.join(PROD, "parts", "shell", "folded", "shell.step")),
         "plate": ((1.3, 1.3, 0.0), os.path.join(PROD, "parts", "plate", "folded", "plate.step"))}

doc = App.newDocument("deck_render")
Import.insert(MASS, doc.Name)
objs = []
for o in list(doc.Objects):
    if o.TypeId != "Part::Feature" or o.Shape.isNull() or not o.Shape.Solids:
        continue
    if o.Label.split("-")[0] in PARTS or o.Label.split("-")[0] in ("pi4", "dac") or o.Label.startswith("fc_massing"):
        continue
    objs.append((o.Label, o.Shape.copy()))
out = App.newDocument("deck_out")
for name, (off, path) in PARTS.items():
    s = Part.read(path)
    s.translate(App.Vector(*off))
    out.addObject("Part::Feature", name).Shape = s
# Pi 4 and DAC Pro split by material (positions from the approved round-4 parameters)
V = App.Vector
def box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
px0, px1, py0, py1, zp, zpt, zh, zht = 4.0, 89.0, 16.0, 72.0, 4.0, 5.4, 14.4, 16.0
eth_y, usb3_y, usb2_y = py1 - 45.75, py1 - 27, py1 - 9
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
]
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
