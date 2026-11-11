"""Runs INSIDE FreeCAD (FreeCADCmd): the kernel side of a hand-folded sheet part. Started by
sheet_cli.py build through freecad_run.py, with its arguments as JSON in FC_JOB (written by
sheet_cli._job): the panels already laid out flat, their cutouts, the folds' hinge lines, and the
folding states to try.

It returns the flat pattern's outline (the union of the panels and fold zones, less cutouts and
reliefs) as loops of lines and arcs for the DXF, any overlap between panels in the flat, and for
every folding state the pairs of panels that collide. Panels joined by a fold are not compared
with each other: a rigid hinge at mid-thickness always overlaps its neighbour by a sliver there.
It writes the folded STEP, STLs for the check renders and an .FCStd laid out in the spec's tree.
"""
import json
import os
import pathlib
import traceback

import FreeCAD as App
import Import
import MeshPart
import Part as OCC

V = App.Vector


def face(e):
    if e["kind"] == "circle":
        return OCC.Face(OCC.Wire([OCC.Circle(V(e["c"][0], e["c"][1], 0), V(0, 0, 1), e["r"]).toShape()]))
    if e["kind"] == "stadium":
        a, b, h = V(*e["a"], 0), V(*e["b"], 0), e["w"] / 2
        d = (b - a).normalize()
        n = V(-d.y, d.x, 0) * h
        edges = [OCC.LineSegment(a - n, b - n).toShape(), OCC.Arc(b - n, b + d * h, b + n).toShape(),
                 OCC.LineSegment(b + n, a + n).toShape(), OCC.Arc(a + n, a - d * h, a - n).toShape()]
        return OCC.Face(OCC.Wire(edges))
    pts = [V(p[0], p[1], 0) for p in e["pts"]]
    return OCC.Face(OCC.makePolygon(pts + [pts[0]]))


def loop(wire):
    """A closed wire as {"kind": "circle"} or {"kind": "poly", "pts", "mids"}: for each edge its
    start point and, when it is an arc, the arc's mid point (None for a line)."""
    edges = wire.OrderedEdges
    if len(edges) == 1 and edges[0].Curve.TypeId == "Part::GeomCircle" and edges[0].isClosed():
        c = edges[0].Curve
        return {"kind": "circle", "c": [c.Center.x, c.Center.y], "r": c.Radius}
    segs = []
    for e in edges:
        a, b = e.valueAt(e.FirstParameter), e.valueAt(e.LastParameter)
        m = e.valueAt((e.FirstParameter + e.LastParameter) / 2) if e.Curve.TypeId != "Part::GeomLine" else None
        segs.append([a, b, m])
    for k, s in enumerate(segs):   # put every edge head to tail
        nxt = segs[(k + 1) % len(segs)]
        if min(s[0].distanceToPoint(nxt[0]), s[0].distanceToPoint(nxt[1])) < min(s[1].distanceToPoint(nxt[0]), s[1].distanceToPoint(nxt[1])) - 1e-9:
            s[0], s[1] = s[1], s[0]
    return {"kind": "poly", "closed": True, "pts": [[s[0].x, s[0].y] for s in segs],
            "mids": [[s[2].x, s[2].y] if s[2] is not None else None for s in segs]}


def mesh(shape, path):
    MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.05, AngularDeflection=0.3, Relative=False).write(str(path))


def sheet_of(doc, name, rows):
    sh = doc.addObject("Spreadsheet::Sheet", name)
    for i, (k, v) in enumerate(rows, start=1):
        sh.set(f"A{i}", str(k))
        sh.set(f"B{i}", str(v))
    return sh


def main(a):
    out, t = pathlib.Path(a["out_dir"]), a["t"]
    panel_faces = {p["id"]: face({"kind": "poly", "pts": p["flat"]}) for p in a["panels"]}

    # flat pattern: no two panels may overlap; the outline is their union with the fold zones
    ids, overlaps = list(panel_faces), []
    for i, pi in enumerate(ids):
        for pj in ids[i + 1:]:
            area = panel_faces[pi].common(panel_faces[pj]).Area
            if area > 1e-6:
                overlaps.append({"pair": [pi, pj], "area_mm2": round(area, 4)})
    # Faces that only share an edge do not merge reliably, solids do: fuse the panels as slabs,
    # refine, and take the slab's bottom face as the flat pattern.
    slab = None
    for f in list(panel_faces.values()) + [face({"kind": "poly", "pts": z}) for z in a["zones"]]:
        s = f.extrude(V(0, 0, 1))
        slab = s if slab is None else slab.fuse(s)
    cuts = [face(e) for p in a["panels"] for e in p["cuts"]] + [face(e) for e in a["reliefs"]]
    if cuts:
        slab = slab.cut(OCC.makeCompound(cuts).extrude(V(0, 0, 3)).translated(V(0, 0, -1)))
    slab = slab.removeSplitter()
    flat = OCC.makeCompound([f for f in slab.Faces if f.BoundBox.ZMax < 1e-6])
    loops = [{"outer": loop(f.OuterWire), "holes": [loop(w) for w in f.Wires if not w.isSame(f.OuterWire)]} for f in flat.Faces]

    # rigid panels, and the folding states
    solids = {}
    for p in a["panels"]:
        s = panel_faces[p["id"]]
        if p["cuts"]:
            s = s.cut(OCC.makeCompound([face(e) for e in p["cuts"]]))
        solids[p["id"]] = s.extrude(V(0, 0, t))
    folds = {f["id"]: f for f in a["folds"]}
    joined = {tuple(sorted(pair)) for pair in a["connected"]}

    def folded(angles):
        res = {}
        for pid, s in solids.items():
            s = s.copy()
            for fid in a["chain"][pid]:
                f = folds[fid]
                if abs(angles.get(fid, 0.0)) > 1e-12:
                    s.rotate(V(f["m0"][0], f["m0"][1], f["hinge_z"]), V(f["d"][0], f["d"][1], 0), angles[fid])
            res[pid] = s
        return res

    def clashes(shapes):
        found, keys = [], list(shapes)
        for i, pi in enumerate(keys):
            for pj in keys[i + 1:]:
                if tuple(sorted((pi, pj))) in joined or not shapes[pi].BoundBox.intersect(shapes[pj].BoundBox):
                    continue
                v = shapes[pi].common(shapes[pj]).Volume
                if v > 1e-3:
                    found.append({"pair": [pi, pj], "volume_mm3": round(v, 4)})
        return found

    states, stls, final = [], [], None
    for n, st in enumerate(a["states"]):
        shapes = folded(st["angles"])
        states.append({"label": st["label"], "sequence": st["sequence"], "interference": clashes(shapes)})
        last = n == len(a["states"]) - 1
        if st["done"] and not last:
            path = out / f"sequence_{st['sequence']}.stl"
            mesh(OCC.makeCompound(list(shapes.values())), path)
            stls.append([str(path), f"after step {st['sequence']}"])
        if last:
            final = shapes
    allshape = OCC.makeCompound(list(final.values()))
    b = allshape.optimalBoundingBox(True, False)
    mesh(allshape, out / "folded.stl")

    doc = App.newDocument("fc_sheet", hidden=True)
    try:
        group = lambda name: doc.addObject("App::DocumentObjectGroup", name)  # noqa: E731
        group("Parameters").addObject(sheet_of(doc, "Params", a["params"]))
        group("Material_Profiles").addObject(sheet_of(doc, "Material", a["material"]))
        group("Manufacturing_Profiles").addObject(sheet_of(doc, "Manufacturing", a["manufacturing"]))
        g_pan, g_fold, g_flat, g_prev = group("Panels"), group("Folds"), group("Flat_Pattern"), group("Folded_Preview")
        for pid, s in solids.items():
            o = doc.addObject("Part::Feature", f"flat_{pid}")
            o.Label, o.Shape = f"{pid} (flat)", s
            g_pan.addObject(o)
        for f in a["folds"]:
            o = doc.addObject("Part::Feature", f"fold_{f['id']}")
            o.Label = f"{f['id']}: {f['label']}"
            o.Shape = OCC.LineSegment(V(f["m0"][0], f["m0"][1], f["hinge_z"]), V(f["m1"][0], f["m1"][1], f["hinge_z"])).toShape()
            g_fold.addObject(o)
        o = doc.addObject("Part::Feature", "FlatOutline")
        o.Shape = flat
        g_flat.addObject(o)
        if a["perforations"]:
            o = doc.addObject("Part::Feature", "Perforations")
            o.Shape = OCC.makeCompound([face(e) if e["kind"] != "line" else
                                        OCC.LineSegment(V(*e["a"], 0), V(*e["b"], 0)).toShape() for e in a["perforations"]])
            g_flat.addObject(o)
        placed = []
        for pid, s in final.items():
            o = doc.addObject("Part::Feature", f"folded_{pid}")
            o.Label, o.Shape = pid, s
            g_prev.addObject(o)
            placed.append(o)
        for name, text in (("Validation", a["validation_text"]), ("Export", a["export_text"])):
            o = doc.addObject("App::TextDocument", name)
            o.Text = text
            group(name + "_").addObject(o)
        doc.recompute()
        doc.saveAs(a["fcstd"])
        Import.export(placed, a["step"])
    finally:
        App.closeDocument(doc.Name)

    return {"freecad_version": ".".join(App.Version()[:3]), "loops": loops, "flat_area": round(flat.Area, 4),
            "flat_overlaps": overlaps, "flat_pieces": len(flat.Faces), "states": states,
            "volume": round(sum(s.Volume for s in final.values()), 4),
            "bbox_min": [round(b.XMin, 4), round(b.YMin, 4), round(b.ZMin, 4)],
            "bbox_max": [round(b.XMax, 4), round(b.YMax, 4), round(b.ZMax, 4)],
            "stls": [[str(out / "folded.stl"), "folded"]] + stls}


args = json.loads(os.environ["FC_JOB"])
if "job_file" in args:      # the job itself can be too long for an environment variable
    with open(args["job_file"], encoding="utf-8") as jf:
        args = json.load(jf)
try:
    result = main(args)
    with open(args["out_json"], "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
except Exception:  # noqa: BLE001
    with open(args["out_json"] + ".error", "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
