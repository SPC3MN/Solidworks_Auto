"""Dimensioned drawing (SLDDRW + PDF + PNG) of a promoted part, from projects/<name>/drawing/drawing.json.

Views are third-angle projections in Z-up orientation. The front elevation looks along +y, the top
view is the plan, and the right view looks along -x. An isometric view goes top right.
These are named views (Z_front, ...) saved into the part, because the standard SolidWorks
views assume Y is up. The sheet scale is picked from a standard list so the views and their
dimension space fit the sheet. A title block is drawn on the sheet.

Each dimension picks one or two model edges by a point ON the edge, in model mm. The pick is mapped
into the view with View.ModelToViewTransform and selected on the sheet. The value SolidWorks
measures is then checked against `expect` (taken from requirements.md, never copied from the model),
so a wrong pick or a wrong model fails the run.

drawing.json:
{
  "title": "...", "sheet": [420, 297],            (mm; default A3 landscape)
  "scale": 2,                                      (optional; otherwise automatic)
  "views": ["front", "top", "right", "isometric"],
  "dims": [
    {"view": "top", "pick": [[x, y, z], [x, y, z]], "kind": "auto|h|v",
     "side": "left|right|above|below", "expect": 85.0, "tol": 0.01, "label": "PCB length"},
    {"view": "top", "pick": [[x, y, z]], "expect": 2.7, "label": "hole dia"}   (one circle -> diameter)
  ],
  "notes": ["All dimensions in mm", ...]
}
Usage: .venv\\Scripts\\python scripts\\drawing.py projects\\<name>
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

import pythoncom
import win32com.client as w
from win32com.client import VARIANT

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import swlib  # noqa: E402
from swlib import NOTHING, Z_UP_VIEWS, _invoke  # noqa: E402

MM = 0.001
SCALES = [10, 5, 4, 2, 1, 1 / 2, 1 / 4, 1 / 5, 1 / 10]
MARGIN, GAP, TB_W, TB_H = 10, 22, 170, 36  # sheet mm: border margin, view gap, title block


def byref():
    return VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)


def arr(vals):
    return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, list(vals))


def open_titles(app):
    out, d = set(), app.GetFirstDocument
    while d is not None:
        out.add(d.GetTitle)
        d = d.GetNext
    return out


def name_views(app, model):
    """Save Z-up named views (Z_front, Z_top, Z_right, Z_isometric) into the part."""
    mu = app.GetMathUtility
    for name, (r, u, t) in Z_UP_VIEWS.items():
        data = [r[0], u[0], t[0], r[1], u[1], t[1], r[2], u[2], t[2], 0, 0, 0, 1, 0, 0, 0]
        model.ActiveView.Orientation3 = w.Dispatch(_invoke(mu, "CreateTransform", arr(data)))
        model.NameView("Z_" + name)


def footprints(bb):
    """Projected (width, height) in model mm of each view for a bbox (lx, ly, lz)."""
    lx, ly, lz = bb
    iso_w = (lx + ly) * 0.7071
    iso_h = (lx + ly) * 0.4082 + lz * 0.8165
    return {"front": (lx, lz), "top": (lx, ly), "right": (ly, lz), "isometric": (iso_w, iso_h)}


def layout(bb, sheet, scale=None):
    """Pick a scale and the sheet centre (mm) of each view (third angle: top above front, right of it)."""
    W, H = sheet
    fp = footprints(bb)
    for s in ([scale] if scale else SCALES):
        fw, fh = fp["front"][0] * s, fp["front"][1] * s
        tw, th = fp["top"][0] * s, fp["top"][1] * s
        rw, rh = fp["right"][0] * s, fp["right"][1] * s
        iso_s = s
        iw, ih = fp["isometric"][0] * s, fp["isometric"][1] * s
        if iw > 0.8 * max(rw, 60) or ih > th + GAP:  # shrink the isometric if it crowds the corner
            iso_s = s / 2
            iw, ih = iw / 2, ih / 2
        col2 = max(rw, iw)
        need_w = MARGIN * 2 + GAP * 3 + fw + col2
        need_h = MARGIN * 2 + TB_H + GAP * 3 + fh + th
        if need_w <= W and need_h <= H or scale:
            x1 = MARGIN + GAP + fw / 2 + max(0, (W - need_w) / 2)  # centre the group across the sheet
            y1 = MARGIN + TB_H + GAP + fh / 2
            x2 = x1 + fw / 2 + GAP + col2 / 2
            y2 = y1 + fh / 2 + GAP + th / 2
            return s, iso_s, {"front": (x1, y1), "top": (x1, y2), "right": (x2, y1), "isometric": (x2, y2)}
    raise RuntimeError("part does not fit the sheet at 1:10")


# Gaps between views are shared, so these sides would put two views' dimensions on top of each other
SHARED_GAPS = {("top", "below"), ("front", "above"), ("front", "right"), ("right", "left")}


def scale_text(s):
    return f"{s:g}:1" if s >= 1 else f"1:{1 / s:g}"


class Drawing:
    def __init__(self, app, part_path, spec):
        self.app, self.spec = app, spec
        self.mu = app.GetMathUtility
        self.part_path = str(part_path)
        self.model = app.OpenDoc6(self.part_path, 1, 1, "", byref(), byref())
        name_views(app, self.model)
        self.model.Save3(1, byref(), byref())
        box = self.model.GetPartBox(True)
        self.bb = [round((box[i + 3] - box[i]) / MM, 3) for i in range(3)]
        self.lo = [box[i] / MM for i in range(3)]
        self.sheet = spec.get("sheet", [420, 297])
        self.doc = app.NewDocument(app.GetUserPreferenceStringValue(10), 12, self.sheet[0] * MM, self.sheet[1] * MM)
        self.doc.GetCurrentSheet.SetSize(12, self.sheet[0] * MM, self.sheet[1] * MM)
        self.doc.GetCurrentSheet.SetScale(1, 1, False, False)  # sheet sketch and notes at 1:1
        self.scale, self.iso_scale, centres = layout(self.bb, self.sheet, spec.get("scale"))
        self.views = {}
        for name in spec.get("views", ["front", "top", "right", "isometric"]):
            cx, cy = centres[name]
            v = self.doc.CreateDrawViewFromModelView3(self.part_path, "Z_" + name, cx * MM, cy * MM, 0)
            if v is None:
                raise RuntimeError(f"view {name} failed")
            v.UseSheetScale = False
            v.ScaleDecimal = self.iso_scale if name == "isometric" else self.scale
            self.views[name] = v
        self.doc.GetCurrentSheet.SetScale(1, 1, False, False)  # the first view auto-scales the sheet
        self.doc.EditRebuild3
        # Re-centre: SolidWorks places the view's own box centre, which differs from the bbox centre
        for name, v in self.views.items():
            v.Position = arr([centres[name][0] * MM, centres[name][1] * MM])
        self.doc.EditRebuild3
        self.stack = {}

    # -- geometry helpers
    def to_sheet(self, view, p):
        t = self.views[view].ModelToViewTransform
        mp = w.Dispatch(_invoke(self.mu, "CreatePoint", arr([c * MM for c in p])))
        x, y = list(w.Dispatch(_invoke(mp, "MultiplyTransform", t)).ArrayData)[:2]
        return x, y

    def outline(self, view):
        return list(self.views[view].GetOutline)  # x0, y0, x1, y1 in m

    def text_point(self, view, picks, side, rank=None):
        o = self.outline(view)
        pts = [self.to_sheet(view, p) for p in picks]
        mx, my = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        k = (view, side)
        n = self.stack.get(k, 0) if rank is None else rank
        self.stack[k] = self.stack.get(k, 0) + 1
        off = (8 + 8 * n) * MM
        if side == "left":
            return o[0] - off, my
        if side == "right":
            return o[2] + off, my
        if side == "above":
            return mx, o[3] + off
        if side == "below":
            return mx, o[1] - off
        # "near" (diameters, radii): push the text out of the view along the line from the view
        # centre through the pick, to just past the outline, so it never sits on the part
        cx, cy = (o[0] + o[2]) / 2, (o[1] + o[3]) / 2
        dx, dy = mx - cx, my - cy
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            dx, dy = 1.0, 1.0
        k = min((o[2] - cx) / abs(dx) if dx else 1e9, (o[3] - cy) / abs(dy) if dy else 1e9)
        sx, sy = (1 if dx >= 0 else -1), (1 if dy >= 0 else -1)
        return cx + dx * k + sx * (6 + 6 * n) * MM, cy + dy * k + sy * (6 + 4 * n) * MM

    # -- dimensions
    def dimension(self, d):
        view = d["view"]
        doc = self.doc
        doc.ClearSelection2(True)
        for i, p in enumerate(d["pick"]):
            sx, sy = self.to_sheet(view, p)
            # model edges first; cylinder outlines in side views are silhouettes, not edges
            if not any(doc.Extension.SelectByID2("", typ, sx, sy, 0, i > 0, 0, NOTHING, 0)
                       for typ in ("EDGE", "SILHOUETTE")):
                return {"label": d.get("label"), "pass": False, "error": f"no edge at pick {p}"}
        side = d.get("side", "near" if len(d["pick"]) == 1 else "above")
        tx, ty = self.text_point(view, d["pick"], side, d.get("_rank"))
        kind = d.get("kind", "auto")
        if kind == "h":
            dd = doc.AddHorizontalDimension2(tx, ty, 0)
        elif kind == "v":
            dd = doc.AddVerticalDimension2(tx, ty, 0)
        else:
            dd = doc.AddDimension2(tx, ty, 0)
        doc.ClearSelection2(True)
        if dd is None:
            return {"label": d.get("label"), "pass": False, "error": "SolidWorks made no dimension"}
        val = round(dd.GetDimension2(0).SystemValue / MM, 4)
        ok = abs(val - d["expect"]) <= d.get("tol", 0.01)
        return {"label": d.get("label"), "view": view, "expected": d["expect"], "actual": val, "pass": ok}

    # -- sheet furniture
    def note(self, text, x, y, height=None):
        n = self.doc.InsertNote(text)
        if n is None:
            return
        ann = n.GetAnnotation
        ann.SetPosition2(x * MM, y * MM, 0)
        if height:
            tf = ann.GetTextFormat(0)
            tf.CharHeight = height * MM
            ann.SetTextFormat(0, False, tf)

    def frame(self, title, project, source):
        W, H = self.sheet
        sm = self.doc.SketchManager
        self.doc.ClearSelection2(True)
        _invoke(self.doc, "EditSheet")  # sketch on the sheet itself, not in the last view
        _invoke(self.doc, "ActivateSheet", self.doc.GetCurrentSheet.GetName)
        sm.AddToDB = True
        lines = [((MARGIN, MARGIN), (W - MARGIN, MARGIN)), ((W - MARGIN, MARGIN), (W - MARGIN, H - MARGIN)),
                 ((W - MARGIN, H - MARGIN), (MARGIN, H - MARGIN)), ((MARGIN, H - MARGIN), (MARGIN, MARGIN))]
        x0, y0 = W - MARGIN - TB_W, MARGIN
        lines += [((x0, y0), (x0, y0 + TB_H)), ((x0, y0 + TB_H), (W - MARGIN, y0 + TB_H)),
                  ((x0, y0 + TB_H / 2), (W - MARGIN, y0 + TB_H / 2)), ((x0 + 110, y0), (x0 + 110, y0 + TB_H / 2))]
        for (a, b), (c, d) in lines:
            sm.CreateLine(a * MM, b * MM, 0, c * MM, d * MM, 0)
        sm.AddToDB = False
        self.doc.ClearSelection2(True)
        self.note(title, x0 + 3, y0 + TB_H - 4, 5)
        self.note(f"{project}   |   {source}", x0 + 3, y0 + TB_H / 2 - 4, 2.5)
        self.note(f"Scale {scale_text(self.scale)} (iso {scale_text(self.iso_scale)})   mm   3rd angle",
                  x0 + 3, y0 + 9, 2.5)
        self.note(dt.date.today().isoformat(), x0 + 113, y0 + 9, 2.5)

    def save(self, out_dir, name):
        out_dir.mkdir(parents=True, exist_ok=True)
        self.doc.ClearSelection2(True)
        self.doc.EditRebuild3
        _invoke(self.doc, "ViewZoomtofit2")
        files = []
        for ext in ("SLDDRW", "pdf", "png"):
            p = out_dir / f"{name}.{ext}"
            self.doc.Extension.SaveAs3(str(p), 0, 1, NOTHING, NOTHING, byref(), byref())
            files.append(p)
        return files


def run(project):
    spec = json.loads((project / "drawing" / "drawing.json").read_text())
    name = project.name
    part = project / "design" / f"{name}.SLDPRT"
    app = swlib.connect()
    before = open_titles(app)
    try:
        drw = Drawing(app, part, spec)
        clash = [d.get("label") for d in spec["dims"] if (d["view"], d.get("side")) in SHARED_GAPS]
        if clash:
            raise SystemExit(f"dims placed in a gap shared with another view (use the outer side): {clash}")
        # stack each side shortest-first, so shorter dimensions sit nearer the part
        groups = {}
        for d in spec["dims"]:
            groups.setdefault((d["view"], d.get("side", "near" if len(d["pick"]) == 1 else "above")), []).append(d)
        for ds in groups.values():
            for r, d in enumerate(sorted(ds, key=lambda d: d["expect"])):
                d["_rank"] = r
        results = [drw.dimension(d) for d in spec["dims"]]
        drw.frame(spec.get("title", name), name, spec.get("source", "see requirements.md"))
        W = drw.sheet[0]
        for i, n in enumerate(spec.get("notes", [])):
            drw.note(n, MARGIN + 4, MARGIN + TB_H - 4 - 4.5 * i, 2.5)
        files = drw.save(project / "drawing", name)
        app.CloseDoc(drw.doc.GetTitle)
        drw.model.Save3(1, byref(), byref())
    finally:
        for t in open_titles(app) - before:
            app.CloseDoc(t)
    ok = all(r["pass"] for r in results)
    report = {"part": name, "time": dt.datetime.now().isoformat(timespec="seconds"), "pass": ok,
              "scale": drw.scale, "bbox": drw.bb, "dims": results, "files": [str(f) for f in files]}
    hist = project / "drawing" / "history"
    hist.mkdir(parents=True, exist_ok=True)
    (hist / f"{dt.datetime.now():%Y%m%dT%H%M%S}.json").write_text(json.dumps(report, indent=1))
    for r in results:
        print("PASS" if r["pass"] else "FAIL", r.get("label"), {k: v for k, v in r.items() if k not in ("label", "pass")})
    print(f"{'PASS' if ok else 'FAIL'} {name}: {sum(r['pass'] for r in results)}/{len(results)} dims, scale {scale_text(drw.scale)}")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=pathlib.Path)
    run(ap.parse_args().project.resolve())
