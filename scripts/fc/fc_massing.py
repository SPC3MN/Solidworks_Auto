"""Runs INSIDE FreeCAD (FreeCADCmd): build the rough 3D massing of one draft option from its
resolved bodies, measure it, check interference and export it. Started by design_cli.py massing
through freecad_run.py, with its arguments as JSON in FC_JOB:

  {"name": "...", "out_dir": "<dir>", "out_json": "<path>", "section_y": 0.0,
   "parts": [{"id": "...", "bodies": [resolved bodies of draft_lib], "instances": [[x, y, z], ...]}]}

A part is its add bodies fused, then its cut bodies removed, once per instance. Writes
massing.step (one product per part instance), massing.stl and section.stl (the half behind the
plane y = section_y, for the section renders) into out_dir. Interference is every pair of part
instances whose common volume exceeds 1e-3 mm^3 (touching faces give zero).
"""
import json
import os
import pathlib
import sys
import traceback

HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]

import FreeCAD as App  # noqa: E402
import Import  # noqa: E402
import MeshPart  # noqa: E402
import Part as OCC  # noqa: E402

import fclib  # noqa: E402

V = App.Vector
AX = {"x": 0, "y": 1, "z": 2}
UNIT = [V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)]


def solid(b):
    s = _solid(b)
    if "rot" in b:
        r = b["rot"]
        s.rotate(V(*r["about"]), UNIT[AX[r["axis"]]], r["deg"])
    return s


def _solid(b):
    at, t = b["at"], b["type"]
    if t == "slab":
        pts = [V(*[at[k] + q[k] for k in range(3)]) for q in b["base"]]
        return OCC.Face(OCC.makePolygon(pts + [pts[0]])).extrude(V(*b["vec"]))
    if t == "box":
        sx, sy, sz = b["size"]
        return _prism("z", at[2], [fclib.rect(at[0], at[1], sx, sy, b["r"])], sz)
    n = UNIT[AX[b["axis"]]]
    i, j = [k for k in range(3) if k != AX[b["axis"]]]
    if t == "cyl":
        s = OCC.makeCylinder(b["d"] / 2, b["h"], V(*at), n)
        return s.cut(OCC.makeCylinder(b["bore"] / 2, b["h"], V(*at), n)) if b["bore"] else s
    if t == "revolve":
        pts = [V(*at) + UNIT[i] * r + n * tt for r, tt in b["profile"]]
        s = OCC.Face(OCC.makePolygon(pts + [pts[0]])).revolve(V(*at), n, 360)
        s = OCC.makeSolid(s) if s.ShapeType == "Shell" else s
        return s.reversed() if s.Volume < 0 else s
    return _prism(b["axis"], at[AX[b["axis"]]], [fclib.polygon([(at[i] + u, at[j] + v) for u, v in b["profile"]])], b["h"])


def _prism(axis, at, profiles, h):
    sk = fclib.Sketch(axis, at)
    for p in profiles:
        p(sk)
    return fclib._face(sk).extrude(sk.normal * h)


def part_shape(part, offset):
    shape = None
    for b in part["bodies"]:
        s = solid(dict(b, at=[a + o for a, o in zip(b["at"], offset)]))
        if not s.isValid() or s.Volume <= 0:
            raise RuntimeError(f"part {part['id']}: a {b['type']} body is not a valid solid")
        shape = s if shape is None else shape.fuse(s) if b["op"] == "add" else shape.cut(s)
    return shape.removeSplitter()


def mesh(shape, path):
    MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.1, AngularDeflection=0.3, Relative=False).write(str(path))


def main(a):
    out = pathlib.Path(a["out_dir"])
    doc = App.newDocument("fc_massing", hidden=True)
    try:
        placed, parts = [], {}
        for p in a["parts"]:
            for k, offset in enumerate(p["instances"]):
                s = part_shape(p, offset)
                label = p["id"] if len(p["instances"]) == 1 else f"{p['id']}-{k + 1}"
                obj = doc.addObject("Part::Feature", label.replace("-", "_"))
                obj.Label, obj.Shape = label, s
                placed.append((p["id"], label, s, obj))
                if k == 0:
                    b = s.optimalBoundingBox(True, False)
                    parts[p["id"]] = {"volume": round(s.Volume, 3), "solids": len(s.Solids), "valid": s.isValid(),
                                      "bbox": [round(b.XLength, 3), round(b.YLength, 3), round(b.ZLength, 3)]}
        doc.recompute()

        found = []
        for i, (pi, li, si, _) in enumerate(placed):
            for pj, lj, sj, _ in placed[i + 1:]:
                if si.BoundBox.intersect(sj.BoundBox):
                    v = si.common(sj).Volume
                    if v > 1e-3:
                        found.append({"pair": sorted([pi, pj]), "labels": [li, lj], "volume_mm3": round(v, 4)})

        allshape = OCC.makeCompound([s for _, _, s, _ in placed])
        b = allshape.optimalBoundingBox(True, False)
        step, stl, sec = out / "massing.step", out / "massing.stl", out / "section.stl"
        Import.export([o for *_, o in placed], str(step))
        mesh(allshape, stl)
        # keep the half behind the section plane (y >= section_y), as seen from the front
        L = 4 * b.DiagonalLength + 100
        front = OCC.makeBox(L, L, L, V(b.XMin - L / 4, a["section_y"] - L, b.ZMin - L / 4))
        halves = [h for h in (s.cut(front) for _, _, s, _ in placed) if not h.isNull() and h.Volume > 1e-6]
        if halves:
            mesh(OCC.makeCompound(halves), sec)
        return {"freecad_version": ".".join(App.Version()[:3]), "parts": parts, "interference": found,
                "bbox": [round(b.XLength, 3), round(b.YLength, 3), round(b.ZLength, 3)],
                "bbox_min": [round(b.XMin, 3), round(b.YMin, 3), round(b.ZMin, 3)],
                "step": str(step), "stl": str(stl), "section_stl": str(sec) if halves else None}
    finally:
        App.closeDocument(doc.Name)


args = json.loads(os.environ["FC_JOB"])
try:
    result = main(args)
    with open(args["out_json"], "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
except Exception:  # noqa: BLE001
    with open(args["out_json"] + ".error", "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
