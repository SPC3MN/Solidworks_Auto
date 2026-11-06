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
  "views": ["front", "top", "isometric"],          (template: top over front on the left, big iso right)
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
import math
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


ISO_SCALES = [10, 8, 6, 5, 4, 3, 2.5, 2, 1.5, 1, 0.75, 1 / 2, 1 / 3, 1 / 4, 1 / 5, 1 / 10]
GAP_ISO = 20  # sheet mm between the left column (and its right-side dimensions) and the isometric
LEFT_MAX = 0.55  # the left column may take at most this share of the usable sheet width


def layout(bb, sheet, scale=None, n_above=1, n_left=1, n_below=0):
    """Sheet template: the top view stacked above the front elevation in a left column (third-angle
    aligned, one scale), and a large isometric filling the right side above the title block, at its
    own scale. Returns (scale, iso_scale, {view: sheet centre in mm})."""
    W, H = sheet
    fp = footprints(bb)
    usable_w = W - 2 * MARGIN
    top_room = 14 + 9 * n_above  # dimension rows stacked above the top view
    left_room = 14 + 9 * n_left  # and to the left of the column
    below_room = 9 * n_below  # dimension rows under the front view (section diameters)
    left_h_max = H - 2 * MARGIN - TB_H - GAP - 10 - top_room - below_room  # bottom band holds the notes
    for s in ([scale] if scale else SCALES):
        fw, fh = fp["front"][0] * s, fp["front"][1] * s
        tw, th = fp["top"][0] * s, fp["top"][1] * s
        col = max(fw, tw)
        if scale or (left_room + col <= LEFT_MAX * usable_w and fh + th <= left_h_max):
            break
    else:
        raise RuntimeError("part does not fit the sheet at 1:10")
    x1 = MARGIN + left_room + col / 2
    # hang the stack from the top border, leaving room for the dimension rows above the top view
    y_top = H - MARGIN - top_room - th / 2
    y_front = y_top - th / 2 - GAP - fh / 2
    # isometric: largest scale that fills the region right of the column, above the title block
    rx0, rx1 = MARGIN + left_room + col + GAP_ISO, W - MARGIN - 10
    ry0, ry1 = MARGIN + TB_H + 10, H - MARGIN - 10
    iw0, ih0 = fp["isometric"]
    iso_s = next((k for k in ISO_SCALES if iw0 * k <= rx1 - rx0 and ih0 * k <= ry1 - ry0), ISO_SCALES[-1])
    return s, iso_s, {"front": (x1, y_front), "top": (x1, y_top),
                      "isometric": ((rx0 + rx1) / 2, (ry0 + ry1) / 2)}


# The gap between the stacked views is shared, so these sides would put both views' dimensions
# on top of each other; the right side faces the isometric across GAP_ISO and is fine.
SHARED_GAPS = {("top", "below"), ("front", "above")}


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
        n_above = sum(1 for d in spec["dims"] if d["view"] == "top" and d.get("side") == "above")
        n_left = max(sum(1 for d in spec["dims"] if d["view"] == v and d.get("side") == "left") for v in ("top", "front"))
        n_below = sum(1 for d in spec["dims"] if d["view"] == "front" and d.get("side") == "below")
        if spec.get("section") and n_below:
            n_below += 2  # the SECTION A-A label sits under the view
        self.scale, self.iso_scale, centres = layout(self.bb, self.sheet, spec.get("scale"), max(1, n_above), max(1, n_left),
                                                     n_below)
        self.views = {}
        section = spec.get("section", False)
        for name in spec.get("views", ["front", "top", "isometric"]):
            if section and name == "front":
                continue  # replaced by the section A-A below
            cx, cy = centres[name]
            v = self.doc.CreateDrawViewFromModelView3(self.part_path, "Z_" + name, cx * MM, cy * MM, 0)
            if v is None:
                raise RuntimeError(f"view {name} failed")
            v.UseSheetScale = False
            v.ScaleDecimal = self.iso_scale if name == "isometric" else self.scale
            self.views[name] = v
        self.doc.GetCurrentSheet.SetScale(1, 1, False, False)  # the first view auto-scales the sheet
        self.doc.EditRebuild3
        if section:
            self.views["front"] = self.section_view()
        # Re-centre: SolidWorks places the view's own box centre, which differs from the bbox centre
        for name, v in self.views.items():
            v.Position = arr([centres[name][0] * MM, centres[name][1] * MM])
        self.doc.EditRebuild3
        self.stack = {}
        self.placed = []  # (spec, DisplayDimension) in placement order

    def section_view(self):
        """Section A-A through the model origin along x, cut in the top view, standing in for the front
        elevation (z up, x right). The cut line is drawn in the top view's own sketch, in view
        coordinates, from +x to -x: drawn the other way the section comes out upside down, and drawn
        in sheet coordinates it does not cut at all (both verified on grindmn_tube)."""
        top = self.views["top"]
        self.doc.ActivateView(top.Name)
        ext = (max(abs(self.lo[0]), abs(self.lo[0] + self.bb[0])) + 5) * MM  # view sketch is in model units
        self.doc.ClearSelection2(True)
        ln = None
        # Some line lengths make CreateLine throw (seen on grindmn_lid at 74 mm); retry a bit longer.
        for k in (1.0, 1.3, 1.7, 2.2):
            try:
                ln = self.doc.SketchManager.CreateLine(ext * k, 0, 0, -ext * k, 0, 0)
                break
            except Exception as e:  # noqa: BLE001
                print("section line retry:", e)
        if ln is None or not ln.Select4(False, NOTHING):
            raise RuntimeError("section line failed")
        v = self.doc.CreateSectionViewAt5(0.1, 0.1, 0, "A", 0, None, 0)
        if v is None:
            raise RuntimeError("section view failed")
        v.UseSheetScale = False
        v.ScaleDecimal = self.scale
        return v

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
            if view == "front" and self.spec.get("section"):
                off += 16 * MM  # clear the SECTION A-A label under the view
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
            # Selection tolerance is in screen pixels: zoomed out on a big sheet, a small hole is a
            # pixel or two and a long edge nearby wins. Zoom the window to the pick first.
            r = 0.008  # +-8 mm of sheet around the pick
            _invoke(doc, "ViewZoomTo2", sx - r, sy - r, 0, sx + r, sy + r, 0)
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
        # DisplayDimension.SetText parts (verified on grindmn_tube): 1 = prefix, 2 = suffix,
        # 3 = callout above. Width dims of turned sections get their diameter sign automatically.
        if d.get("prefix"):
            dd.SetText(1, d["prefix"])
        if d.get("suffix"):
            dd.SetText(2, d["suffix"])
        self.placed.append((d, dd))
        val = round(dd.GetDimension2(0).SystemValue / MM, 4)
        ok = abs(val - d["expect"]) <= d.get("tol", 0.01)
        return {"label": d.get("label"), "view": view, "expected": d["expect"], "actual": val, "pass": ok}

    # -- overlap rule: no dimension text may touch another dimension's text or lines, or a view
    CHAR_W = 0.6   # text width per character, as a share of text height (measured: ' 85.00 ' = 14.2 mm at 3.5)
    PAD = 0.8      # clearance around text, sheet mm

    def _geom(self, dd):
        """(text boxes, line segments) of one display dimension, in sheet mm. A box is
        (x, y, angle, w, h) with (x, y) at the start of the text baseline."""
        dat = dd.GetDisplayData
        boxes = []
        for i in range(dat.GetTextCount):
            s = dat.GetTextAtIndex(i).replace("<MOD-DIAM>", "Ø")
            if not s.strip():
                continue
            x, y, _ = [v / MM for v in dat.GetTextPositionAtIndex(i)]
            h = dat.GetTextHeightAtIndex(i) / MM
            boxes.append((x, y, dat.GetTextAngleAtIndex(i), len(s) * self.CHAR_W * h, h))
        lines = []
        for i in range(dat.GetLineCount):
            a = list(dat.GetLineAtIndex3(i))
            lines.append(((a[4] / MM, a[5] / MM), (a[7] / MM, a[8] / MM)))
        return boxes, lines

    @staticmethod
    def _local(box, p):
        x, y, ang, _, _ = box
        c, s = math.cos(-ang), math.sin(-ang)
        dx, dy = p[0] - x, p[1] - y
        return dx * c - dy * s, dx * s + dy * c

    def _box_hits_segment(self, box, seg):
        """Segment vs padded text rectangle, tested in the text's own frame (Liang-Barsky clip)."""
        _, _, _, w, h = box
        (x0, y0), (x1, y1) = self._local(box, seg[0]), self._local(box, seg[1])
        lo = (-self.PAD, -0.25 * h - self.PAD)
        hi = (w + self.PAD, 1.1 * h + self.PAD)
        t0, t1 = 0.0, 1.0
        for p0, d, a, b in ((x0, x1 - x0, lo[0], hi[0]), (y0, y1 - y0, lo[1], hi[1])):
            if abs(d) < 1e-12:
                if p0 < a or p0 > b:
                    return False
                continue
            ta, tb = (a - p0) / d, (b - p0) / d
            t0, t1 = max(t0, min(ta, tb)), min(t1, max(ta, tb))
            if t0 > t1:
                return False
        return True

    def _box_corners(self, box):
        x, y, ang, w, h = box
        c, s = math.cos(ang), math.sin(ang)
        pts = [(-self.PAD, -0.25 * h - self.PAD), (w + self.PAD, -0.25 * h - self.PAD),
               (w + self.PAD, 1.1 * h + self.PAD), (-self.PAD, 1.1 * h + self.PAD)]
        return [(x + u * c - v * s, y + u * s + v * c) for u, v in pts]

    def _box_hits_box(self, a, b):
        ca, cb = self._box_corners(a), self._box_corners(b)
        edges = lambda cs: list(zip(cs, cs[1:] + cs[:1]))  # noqa: E731
        return (any(self._box_hits_segment(a, e) for e in edges(cb))
                or any(self._box_hits_segment(b, e) for e in edges(ca))
                or self._inside(cb[0], ca) or self._inside(ca[0], cb))

    @staticmethod
    def _inside(p, poly):
        sgn = None
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
            cr = (x1 - x0) * (p[1] - y0) - (y1 - y0) * (p[0] - x0)
            if sgn is None:
                sgn = cr > 0
            elif (cr > 0) != sgn:
                return False
        return True

    def _conflicts(self, k, geoms):
        """What dimension k's text hits: other dims' text and lines, and any view outline."""
        boxes, _ = geoms[k]
        hits = []
        for j, (ob, ol) in enumerate(geoms):
            if j == k:
                continue
            if any(self._box_hits_box(b, o) for b in boxes for o in ob) or \
               any(self._box_hits_segment(b, seg) for b in boxes for seg in ol):
                hits.append(self.placed[j][0].get("label"))
        for name, v in self.views.items():
            x0, y0, x1, y1 = [c / MM for c in v.GetOutline]
            rect = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            if any(self._box_hits_segment(b, e) or self._inside(self._box_corners(b)[0], rect)
                   for b in boxes for e in zip(rect, rect[1:] + rect[:1])):
                hits.append(f"view:{name}")
        return hits

    def _candidates(self, d, pos):
        """Text positions to try, nearest first. Along the dimension line, so the text slides
        clear of crossing extension lines and outside short spans; then one or two rows further out."""
        x, y = pos[0] / MM, pos[1] / MM
        side = d.get("side", "near" if len(d["pick"]) == 1 else "above")
        along = (0, 1) if side in ("left", "right") else (1, 0)
        out = {"left": (-1, 0), "right": (1, 0), "above": (0, 1), "below": (0, -1)}.get(side)
        shifts = sorted({s * k for k in range(1, 21) for s in (3, -3)}, key=abs)
        rows = [0, 9, 18] if out else [0]
        if not out:  # diameters: walk the leader outwards in a ring of directions
            return [(x + r * math.cos(a), y + r * math.sin(a))
                    for r in (0, 6, 12, 18) for a in [i * math.pi / 4 for i in range(8)]][1:]
        return [(x + out[0] * r + along[0] * s, y + out[1] * r + along[1] * s)
                for r in rows for s in [0] + shifts if (r, s) != (0, 0)]

    def resolve_overlaps(self, passes=3):
        """Apply the overlap rule; returns the overlaps that are left (label -> what it hits)."""
        for _ in range(passes):
            geoms = [self._geom(dd) for _, dd in self.placed]
            moved = False
            for k, (d, dd) in enumerate(self.placed):
                if not self._conflicts(k, geoms):
                    continue
                ann = dd.GetAnnotation
                start = list(ann.GetPosition)
                for cx, cy in self._candidates(d, start):
                    ann.SetPosition2(cx * MM, cy * MM, start[2])
                    geoms[k] = self._geom(dd)
                    if not self._conflicts(k, geoms):
                        moved = True
                        break
                else:
                    ann.SetPosition2(*start)
                    geoms[k] = self._geom(dd)
            if not moved:
                break
        geoms = [self._geom(dd) for _, dd in self.placed]
        return {self.placed[k][0].get("label"): h for k in range(len(self.placed))
                if (h := self._conflicts(k, geoms))}

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
        left = drw.resolve_overlaps()
        results.append({"label": "layout: no overlapping dimensions", "pass": not left, "overlaps": left})
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
