"""Runs INSIDE FreeCAD (FreeCADCmd): place the promoted parts of an assembly.json, measure, check
interference, save and export. Started by assembly.py --backend freecad through freecad_run.py, with its
arguments as JSON in FC_JOB:

  {"components": [{"label": "...", "part": "...", "step": "<part STEP>", "matrix": [16 numbers, rows]}],
   "fcstd": "<path>", "step": "<path>", "stl": "<path>", "out_json": "<path>"}

Each part is read once from its promoted STEP (projects/<part>/exports/<part>.step, CAD-neutral) and placed
as one Part::Feature per component inside an App::Part, so the STEP has one product per component.
Interference is every pair whose common volume exceeds 1e-3 mm^3 (touching faces give zero), after a
bounding-box prefilter. The pipeline side (assembly.py) compares the results with assembly.json.
"""
import json
import os
import traceback

import FreeCAD as App
import Import
import MeshPart
import Part


def main(a):
    doc = App.newDocument("fc_assembly", hidden=True)
    try:
        root = doc.addObject("App::Part", "Assembly")
        shapes, placed = {}, []
        for c in a["components"]:
            if c["step"] not in shapes:
                shapes[c["step"]] = Part.read(c["step"])
            s = shapes[c["step"]].copy()
            s.transformShape(App.Matrix(*c["matrix"]), False, False)
            obj = doc.addObject("Part::Feature", c["label"].replace("-", "_"))
            obj.Label, obj.Shape = c["label"], s
            root.addObject(obj)
            placed.append((c, obj))
        doc.recompute()

        allshape = Part.makeCompound([o.Shape for _, o in placed])
        b = allshape.optimalBoundingBox(True, False)
        found = []
        boxes = [o.Shape.BoundBox for _, o in placed]
        for i, (ci, oi) in enumerate(placed):
            for j in range(i + 1, len(placed)):
                cj, oj = placed[j]
                if not boxes[i].intersect(boxes[j]):
                    continue
                v = oi.Shape.common(oj.Shape).Volume
                if v > 1e-3:
                    found.append({"pair": sorted([ci["part"], cj["part"]]), "labels": [ci["label"], cj["label"]],
                                  "volume_mm3": round(v, 4)})

        doc.saveAs(a["fcstd"])
        Import.export([o for _, o in placed], a["step"])
        MeshPart.meshFromShape(Shape=allshape, LinearDeflection=0.05, AngularDeflection=0.2,
                               Relative=False).write(a["stl"])
        return {"freecad_version": ".".join(App.Version()[:3]), "components": len(placed),
                "bbox": [round(b.XLength, 3), round(b.YLength, 3), round(b.ZLength, 3)],
                "bbox_min": [round(b.XMin, 3), round(b.YMin, 3), round(b.ZMin, 3)],
                "interference": found}
    finally:
        App.closeDocument(doc.Name)


args = json.loads(os.environ["FC_JOB"])
try:
    out = main(args)
    with open(args["out_json"], "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
except Exception:  # noqa: BLE001
    with open(args["out_json"] + ".error", "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
