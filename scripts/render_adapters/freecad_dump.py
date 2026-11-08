"""Runs INSIDE FreeCAD (FreeCADCmd / freecadcmd): walk an .FCStd, export one STEP per unique
part, write the raw product data as JSON. Started by scripts/render_adapters/freecad.py, which
passes its arguments in the RENDER_FC_ARGS environment variable (FreeCADCmd treats extra
command-line words as files to open).

The document is opened, read and closed; it is never recomputed or saved.

Walk (FreeCAD 0.21 / 1.x object model):
- leaves: Part::Feature and everything derived from it (PartDesign::Body, Part primitives and
  booleans, imported solids, Assembly4 / A2plus part copies) that has faces; sketches skipped
- containers: App::Part (has a Placement; the 1.x Assembly derives from it) and
  App::DocumentObjectGroup (no Placement) - recursed
- links: App::Link (also arrays through ElementList). The link's LinkPlacement replaces the
  linked object's own placement unless LinkTransform is true, in which case it is applied on
  top. Links to the same object become one part with several components (instances).
Every leaf's geometry is exported in its own coordinates (Shape placement removed) and the
placement chain becomes the component transform, in mm.

Independent check: FreeCAD's own evaluation of every visible root (Part.getShape, which
resolves links and containers itself) gives the overall bbox that the walk must reproduce.
"""
import json
import os
import re
import traceback

import FreeCAD as App
import Part

SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def clean(s):
    return SAFE.sub("_", s).strip("_") or "part"


def rows(m):
    return [[m.A11, m.A12, m.A13, m.A14], [m.A21, m.A22, m.A23, m.A24],
            [m.A31, m.A32, m.A33, m.A34], [m.A41, m.A42, m.A43, m.A44]]


def bbox(shape):
    try:
        b = shape.optimalBoundingBox(True, False)  # tight (triangulation), FreeCAD 0.20+
    except Exception:  # noqa: BLE001
        b = shape.BoundBox
    return [b.XMin, b.YMin, b.ZMin], [b.XMax, b.YMax, b.ZMax]


def derived(o, t):
    try:
        return o.isDerivedFrom(t)
    except Exception:  # noqa: BLE001
        return False


def is_leaf(o):
    if not derived(o, "Part::Feature") or derived(o, "Part::Part2DObject"):
        return False
    try:
        return not o.Shape.isNull() and len(o.Shape.Faces) > 0
    except Exception:  # noqa: BLE001
        return False


def is_link(o):
    return o.TypeId in ("App::Link", "App::LinkElement", "App::LinkGroup") or derived(o, "App::Link")


def is_container(o):
    return derived(o, "App::Part") or derived(o, "App::DocumentObjectGroup")


def main():
    a = json.loads(os.environ["RENDER_FC_ARGS"])
    out_dir = a["parts_dir"]
    os.makedirs(out_dir, exist_ok=True)
    doc = App.openDocument(a["file"])
    root = clean(doc.Label or doc.Name)
    parts, comps, hierarchy, warnings = {}, [], [{"id": root, "parent": None, "kind": "assembly"}], []
    keys = {}

    def add_part(o):
        key = f"{o.Document.Name}#{o.Name}"
        if key in keys:
            return keys[key]
        pid, k = clean(o.Label), 2
        while pid in parts:
            pid, k = f"{clean(o.Label)}_{k}", k + 1
        keys[key] = pid
        s = o.Shape.copy()
        s.Placement = App.Placement()
        path = os.path.join(out_dir, f"{pid}.step")
        s.exportStep(path)
        lo, hi = bbox(s)
        mat = getattr(o, "ShapeMaterial", None)  # FreeCAD 1.0+ material, optional
        parts[pid] = {"file": path, "bbox_min": lo, "bbox_max": hi, "label": o.Label, "object": key,
                      "material_name": getattr(mat, "Name", "") or "", "solids": len(s.Solids)}
        return pid

    def walk(o, parent_mat, parent_id, path, visible, seen):
        if o in seen:  # guard against link cycles
            return
        seen = seen | {o}
        vis = visible and bool(getattr(o, "Visibility", True))
        my_path = f"{path}/{o.Name}" if path else o.Name
        if is_link(o):
            elems = list(getattr(o, "ElementList", []) or [])
            if elems:
                m = parent_mat.multiply(o.Placement.toMatrix())
                hierarchy.append({"id": my_path, "parent": parent_id, "kind": "subassembly", "label": o.Label})
                for el in elems:
                    walk(el, m, my_path, my_path, vis, seen)
                return
            target = o.getLinkedObject(True)
            if target is None or target is o:
                warnings.append(f"{o.Label}: link without target")
                return
            m = parent_mat.multiply(o.LinkPlacement.toMatrix())
            if is_leaf(target):
                local = target.Shape.Placement.toMatrix() if getattr(o, "LinkTransform", False) else App.Matrix()
                emit(target, m.multiply(local), parent_id, my_path, vis, o.Label)
            elif is_container(target):
                if getattr(o, "LinkTransform", False) and hasattr(target, "Placement"):
                    m = m.multiply(target.Placement.toMatrix())
                hierarchy.append({"id": my_path, "parent": parent_id, "kind": "subassembly", "label": o.Label})
                for ch in target.Group:
                    walk(ch, m, my_path, my_path, vis, seen)
            else:
                warnings.append(f"{o.Label}: link to {target.TypeId}, skipped")
            return
        if is_leaf(o):
            emit(o, parent_mat.multiply(o.Shape.Placement.toMatrix()), parent_id, my_path, vis, o.Label)
            return
        if is_container(o):
            m = parent_mat.multiply(o.Placement.toMatrix()) if derived(o, "App::Part") else parent_mat
            hierarchy.append({"id": my_path, "parent": parent_id, "kind": "subassembly", "label": o.Label})
            for ch in o.Group:
                walk(ch, m, my_path, my_path, vis, seen)

    def emit(o, m, parent_id, cid, vis, label):
        pid = add_part(o)
        s = o.Shape.copy()
        s.Placement = App.Placement(m)
        wlo, whi = bbox(s)
        comps.append({"id": cid, "name": label, "label": label, "parent": parent_id, "part": pid, "transform": rows(m),
                      "visible": vis, "world_bbox_mm": [wlo, whi], "world_shape": s})

    for o in doc.RootObjects:
        walk(o, App.Matrix(), root, "", True, frozenset())

    # whole product as one STEP (cross-check in Blender) and FreeCAD's own overall bbox.
    # One object per component, so the STEP holds one product each (a single compound
    # would import as one mesh).
    shown = [c for c in comps if c["visible"]]
    if shown:
        import Import
        tmp = App.newDocument("render_assembly_step", hidden=True)
        objs = []
        for c in shown:
            obj = tmp.addObject("Part::Feature", clean(c["id"]))
            obj.Shape, obj.Label = c["world_shape"], c["name"]
            objs.append(obj)
        Import.export(objs, a["assembly_step"])
        App.closeDocument(tmp.Name)
    ref = []
    for o in doc.RootObjects:
        if not getattr(o, "Visibility", True):
            continue
        try:
            s = Part.getShape(o)
            if not s.isNull() and s.Faces:
                ref.append(bbox(s))
        except Exception as e:  # noqa: BLE001
            warnings.append(f"Part.getShape({o.Label}): {e}")
    for c in comps:
        del c["world_shape"]
    out = {"root": root, "file": a["file"], "freecad_version": ".".join(App.Version()[:3]),
           "hierarchy": hierarchy, "parts": parts, "components": comps, "warnings": warnings,
           "freecad_bbox": [[min(b[0][i] for b in ref) for i in range(3)], [max(b[1][i] for b in ref) for i in range(3)]] if ref else None}
    App.closeDocument(doc.Name)
    with open(a["out_json"], "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)


try:
    main()
except Exception:  # noqa: BLE001
    with open(json.loads(os.environ["RENDER_FC_ARGS"])["out_json"] + ".error", "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
    raise
