"""Capture an existing SolidWorks assembly (read-only) so it can be rebuilt with simple parts.

Opens the source assembly read-only, walks every leaf component (through virtual and real
sub-assemblies), and writes assemblies/<name>/capture.json:
  - leaves: instance name, source file, transform (row-vector 3x3 + translation in mm, as in
    Component2.Transform2.ArrayData) and the component box in assembly coordinates
  - skipped: suppressed, hidden, missing and empty components, with the reason
  - parts: part-frame box, volume, face and body count of every unique source file
  - interference: colliding instance pairs in the original (the baseline), with --interference
  - bbox of the whole original and the total face count of the captured leaves
Sub-assemblies whose file name is in x8020_map.json "collapse" become a single leaf.
Self-check: each leaf's transformed part box must match its component box.

    .venv\\Scripts\\python scripts\\asm_capture.py TANK.SLDASM assemblies\\tank --interference
"""
import argparse
import json
import os
import pathlib
import sys
import time

import pythoncom
import win32com.client
from win32com.client import VARIANT

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import swlib  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
MM = 0.001


def byref():
    return VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)


def titles(app):
    out, d = set(), app.GetFirstDocument
    while d is not None:
        out.add(d.GetTitle)
        d = d.GetNext
    return out


def xform_of(comp):
    a = list(comp.Transform2.ArrayData)
    return [round(v, 9) for v in a[:9]] + [round(v / MM, 6) for v in a[9:12]]


def apply(x, p):
    """Row-vector convention (verified in docs/solidworks_findings.md): p' = p R + t."""
    return [p[0] * x[0] + p[1] * x[3] + p[2] * x[6] + x[9],
            p[0] * x[1] + p[1] * x[4] + p[2] * x[7] + x[10],
            p[0] * x[2] + p[1] * x[5] + p[2] * x[8] + x[11]]


def box_of(x, box):
    """Axis-aligned box of a part-frame box [x0, y0, z0, x1, y1, z1] after transform x."""
    pts = [apply(x, (box[i], box[1 + j], box[2 + k])) for i in (0, 3) for j in (0, 3) for k in (0, 3)]
    return [min(p[a] for p in pts) for a in range(3)] + [max(p[a] for p in pts) for a in range(3)]


def walk(comp, collapse, leaves, skipped, hidden_parent=False):
    for c in comp.GetChildren or ():
        name, path = c.Name2, c.GetPathName
        fname = os.path.basename(path)
        hidden = hidden_parent or c.Visible == 0
        sup = c.IsSuppressed  # late binding exposes it as a property or a method, depending on the object
        if callable(sup):
            sup = sup()
        if sup:
            skipped.append({"name": name, "file": fname, "reason": "suppressed"})
            continue
        if hidden:
            skipped.append({"name": name, "file": fname, "reason": "hidden"})
            continue
        is_asm = path.lower().endswith(".sldasm")
        virtual = "^" in fname
        if not virtual and not os.path.exists(path):
            skipped.append({"name": name, "file": fname, "reason": f"missing file {path}"})
            continue
        if is_asm and fname not in collapse:
            walk(c, collapse, leaves, skipped, hidden)
            continue
        b = c.GetBox(False, False)
        leaves.append({"name": name, "file": fname, "path": path, "xform": xform_of(c),
                       "comp_box": [round(v / MM, 3) for v in b] if b else None})


def part_info(app, path):
    pre = titles(app)
    is_asm = path.lower().endswith(".sldasm")
    doc = app.OpenDoc6(path, 2 if is_asm else 1, 1 | 2, "", byref(), byref())
    if doc is None:
        return {"error": "open failed"}
    try:
        if is_asm:
            b = doc.GetBox(0)
            faces, n = 0, 0
            for c in doc.GetComponents(False) or ():
                if c.GetPathName.lower().endswith(".sldprt"):
                    m = c.GetModelDoc2
                    if m is None:
                        c.SetSuppression2(2)  # resolve
                        m = c.GetModelDoc2
                    n += 1
                    if m is not None:
                        faces += sum(bd.GetFaceCount() for bd in m.GetBodies2(0, False) or ())
            return {"box": [round(v / MM, 3) for v in b], "faces": faces, "parts": n, "assembly": True}
        b = doc.GetPartBox(True)
        bodies = doc.GetBodies2(0, False) or ()
        return {"box": [round(v / MM, 3) for v in b],
                "volume": round(doc.Extension.CreateMassProperty.Volume * 1e9, 3) if bodies else 0.0,
                "faces": sum(bd.GetFaceCount() for bd in bodies), "bodies": len(bodies)}
    finally:
        for t in titles(app) - pre:
            app.CloseDoc(t)


def interferences(doc):
    idm = doc.InterferenceDetectionManager
    idm.TreatCoincidenceAsInterference = False
    idm.TreatSubAssembliesAsComponents = False
    idm.IncludeMultibodyPartInterferences = False
    found = []
    for itf in idm.GetInterferences or ():
        names = sorted(c.Name2 for c in itf.Components)
        found.append({"pair": names, "volume_mm3": round(itf.Volume / MM ** 3, 3)})
    idm.Done
    return found


def run(src, folder, do_itf):
    mp = json.loads((ROOT / "assemblies" / "x8020_map.json").read_text())
    collapse = set(mp.get("collapse", []))
    app = swlib.connect()
    before = titles(app)
    t0 = time.time()
    out = {"source": str(src)}
    try:
        e = byref()
        doc = app.OpenDoc6(str(src), 2, 1 | 2, "", e, byref())
        if doc is None:
            raise RuntimeError(f"could not open {src} (error {e.value})")
        doc.ResolveAllLightWeightComponents(False)
        b = doc.GetBox(0)
        out["bbox_box"] = [round(v / MM, 3) for v in b]
        out["bbox"] = [round((b[i + 3] - b[i]) / MM, 3) for i in range(3)]
        leaves, skipped = [], []
        root = doc.ConfigurationManager.ActiveConfiguration.GetRootComponent3(True)
        walk(root, collapse, leaves, skipped)
        out["leaves"], out["skipped"] = leaves, skipped
        print(f"{len(leaves)} leaves, {len(skipped)} skipped ({time.time() - t0:.0f} s)")
        if do_itf:
            t1 = time.time()
            out["interference"] = interferences(doc)
            out["interference_seconds"] = round(time.time() - t1, 1)
            print(f"{len(out['interference'])} interferences ({out['interference_seconds']} s)")
        app.CloseDoc(doc.GetTitle)
        for t in titles(app) - before:
            app.CloseDoc(t)
        parts = {}
        for lf in leaves:
            if lf["file"] not in parts:
                parts[lf["file"]] = part_info(app, lf["path"])
        out["parts"] = parts
    finally:
        for t in titles(app) - before:
            app.CloseDoc(t)
    # drop empty parts (no bodies), self-check transforms against component boxes
    keep = []
    worst = 0.0
    for lf in out["leaves"]:
        info = out["parts"][lf["file"]]
        if not info.get("assembly") and info.get("bodies", 0) == 0:
            out["skipped"].append({"name": lf["name"], "file": lf["file"], "reason": "no bodies"})
            continue
        if lf["comp_box"] and "box" in info:
            pred = box_of(lf["xform"], info["box"])
            dev = max(abs(a - c) for a, c in zip(pred, lf["comp_box"]))
            lf["box_dev"] = round(dev, 3)
            worst = max(worst, dev)
        keep.append(lf)
    out["leaves"] = keep
    out["faces_total"] = sum(out["parts"][lf["file"]].get("faces", 0) for lf in keep)
    out["box_dev_max"] = round(worst, 3)
    out["seconds"] = round(time.time() - t0, 1)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "capture.json").write_text(json.dumps(out, indent=1))
    by = {}
    for lf in keep:
        by[lf["file"]] = by.get(lf["file"], 0) + 1
    for f, n in sorted(by.items()):
        info = out["parts"][f]
        print(f"  {n:3d} x {f:45s} faces {info.get('faces')}")
    for s in out["skipped"]:
        print("  skipped", s["name"], "-", s["reason"])
    print(f"leaves {len(keep)}, faces {out['faces_total']}, bbox {out['bbox']}, "
          f"worst box deviation {out['box_dev_max']} mm, {out['seconds']} s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=pathlib.Path)
    ap.add_argument("folder", type=pathlib.Path)
    ap.add_argument("--interference", action="store_true")
    a = ap.parse_args()
    run(a.source.resolve(), a.folder.resolve(), a.interference)
