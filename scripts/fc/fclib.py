"""FreeCAD backend for model scripts: the swlib API on OpenCASCADE booleans. All inputs in mm.

Runs inside FreeCADCmd. fc_job.py registers this module as `swlib` (and fc_params as
`sw_params`), so model scripts and the shared generators run unchanged on either backend.

Same conventions as swlib: height is +Z, profile coordinates are model coordinates on the
sketch plane, (x, y) for axis="z", (x, z) for axis="y" and (y, z) for axis="x". Extrudes go
toward +axis (down=True: -axis), blind cuts toward -axis (down=False: +axis), and depth=None
cuts through everything both ways.

Every feature is kept as a replayable op, so a feature's volume can be measured by rebuilding
without it (the counterpart of suppressing it in SolidWorks). Faces and edges are picked by
the point nearest them, as in swlib, and the picks are repeated on every replay.
"""
import math

import FreeCAD as App
import Part as OCC

V = App.Vector
EPS = 1e-6

# axis -> (model point from (a, b) on the plane at offset `at`, plane normal)
PLANES = {
    "z": (lambda a, b, at: V(a, b, at), V(0, 0, 1)),
    "y": (lambda a, b, at: V(a, at, b), V(0, 1, 0)),
    "x": (lambda a, b, at: V(at, a, b), V(1, 0, 0)),
}


# ---------------------------------------------------------------- profiles
# A profile is a callable that draws closed geometry into a Sketch (the counterpart of the
# SolidWorks SketchManager), so closures that call other profiles (details.ring) still work.

class Sketch:
    def __init__(self, axis, at):
        self.axis, self.at = axis, at
        self._pt, self.normal = PLANES[axis]
        self.wires, self.edges = [], []

    def p(self, a, b):
        return self._pt(a, b, self.at)

    def closed(self, edges):
        self.wires.append(OCC.Wire(edges))


def _arc3(sk, c, s, e, ccw=True):
    """Arc from s to e about c (2D), counter-clockwise in the profile plane unless ccw=False."""
    r = math.dist(c, s)
    a0, a1 = math.atan2(s[1] - c[1], s[0] - c[0]), math.atan2(e[1] - c[1], e[0] - c[0])
    if ccw and a1 <= a0:
        a1 += 2 * math.pi
    if not ccw and a1 >= a0:
        a1 -= 2 * math.pi
    am = (a0 + a1) / 2
    m = (c[0] + r * math.cos(am), c[1] + r * math.sin(am))
    return OCC.Arc(sk.p(*s), sk.p(*m), sk.p(*e)).toShape()


def _poly_edges(sk, pts):
    pts = list(pts) + [pts[0]]
    return [OCC.LineSegment(sk.p(*a), sk.p(*b)).toShape() for a, b in zip(pts, pts[1:]) if math.dist(a, b) > EPS]


def rect(cx, cy, w, h, r=0.0):
    """Rectangle centred at (cx, cy), optional corner radius r."""
    def draw(sk):
        x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
        if r <= 0:
            sk.closed(_poly_edges(sk, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]))
            return
        L = lambda a, b: OCC.LineSegment(sk.p(*a), sk.p(*b)).toShape()  # noqa: E731
        edges = []
        for (a, b), (c, s, e) in (
            (((x0 + r, y0), (x1 - r, y0)), ((x1 - r, y0 + r), (x1 - r, y0), (x1, y0 + r))),
            (((x1, y0 + r), (x1, y1 - r)), ((x1 - r, y1 - r), (x1, y1 - r), (x1 - r, y1))),
            (((x1 - r, y1), (x0 + r, y1)), ((x0 + r, y1 - r), (x0 + r, y1), (x0, y1 - r))),
            (((x0, y1 - r), (x0, y0 + r)), ((x0 + r, y0 + r), (x0, y0 + r), (x0 + r, y0))),
        ):
            if math.dist(a, b) > EPS:
                edges.append(L(a, b))
            edges.append(_arc3(sk, c, s, e))
        sk.closed(edges)
    return draw


def circle(cx, cy, d):
    def draw(sk):
        sk.closed([OCC.Circle(sk.p(cx, cy), sk.normal, d / 2).toShape()])
    return draw


def polygon(points):
    """Closed polyline through [(x, y), ...]."""
    def draw(sk):
        sk.closed(_poly_edges(sk, points))
    return draw


def slot(cx, cy, length, width, angle_deg=0.0):
    """Straight slot (stadium), overall length `length`, centred at (cx, cy)."""
    def draw(sk):
        a, r = math.radians(angle_deg), width / 2
        half = (length - width) / 2
        ux, uy = math.cos(a), math.sin(a)
        nx, ny = -uy, ux
        c1, c2 = (cx - half * ux, cy - half * uy), (cx + half * ux, cy + half * uy)
        q = lambda c, s: (c[0] + s * r * nx, c[1] + s * r * ny)  # noqa: E731
        edges = []
        if half > EPS:
            edges.append(OCC.LineSegment(sk.p(*q(c1, -1)), sk.p(*q(c2, -1))).toShape())
        edges.append(_arc3(sk, c2, q(c2, -1), q(c2, 1)))
        if half > EPS:
            edges.append(OCC.LineSegment(sk.p(*q(c2, 1)), sk.p(*q(c1, 1))).toShape())
        edges.append(_arc3(sk, c1, q(c1, 1), q(c1, -1)))
        sk.closed(edges)
    return draw


def path(segments):
    """Open path for a sweep: ["line", (a, b), (a, b)] or ["arc", centre, start, end]
    (arcs under 180 degrees; direction worked out from the points)."""
    def draw(sk):
        for seg in segments:
            if seg[0] == "line":
                sk.edges.append(OCC.LineSegment(sk.p(*seg[1]), sk.p(*seg[2])).toShape())
            else:
                c, s, e = seg[1:]
                ccw = (s[0] - c[0]) * (e[1] - c[1]) - (s[1] - c[1]) * (e[0] - c[0]) > 0
                sk.edges.append(_arc3(sk, c, s, e, ccw))
    return draw


def path_length(segments):
    total = 0.0
    for seg in segments:
        if seg[0] == "line":
            total += math.dist(seg[1], seg[2])
        else:
            c, s, e = seg[1:]
            r = math.dist(c, s)
            a = abs(math.atan2((s[0] - c[0]) * (e[1] - c[1]) - (s[1] - c[1]) * (e[0] - c[0]),
                               (s[0] - c[0]) * (e[0] - c[0]) + (s[1] - c[1]) * (e[1] - c[1])))
            total += r * a
    return total


def _face(sk):
    if not sk.wires:
        raise ValueError("empty sketch")
    # Bullseye: nested wires become holes (rings, ports), separate wires separate faces.
    f = OCC.makeFace(sk.wires, "Part::FaceMakerBullseye")
    if not f.isValid() or f.Area <= EPS:
        raise ValueError("invalid profile (self-crossing or overlapping contours)")
    return f


# ---------------------------------------------------------------- part

def render(doc, out_dir, views=("isometric", "top", "front", "right"), size=None):
    """Headless FreeCAD has no viewport: check renders are made in Blender by the pipeline."""
    return []


class Part:
    """Same method set as swlib.Part. `app` is ignored (kept for the model scripts' signature)."""

    def __init__(self, app=None):
        self.ops = []          # (name, fn(shape, skip) -> shape)
        self.tools = {}        # name -> ("add" | "cut", tool solid) for patterns
        self.params, self.dims = {}, {}
        self._shape = None

    # build() returns part.doc in the model scripts; here that is the Part itself.
    @property
    def doc(self):
        return self

    def close_prefs(self):
        pass

    @property
    def shape(self):
        return self._shape

    def _add_op(self, name, fn):
        if any(n == name for n, _ in self.ops):
            raise ValueError(f"duplicate feature name {name}")
        self.ops.append((name, fn))
        self._shape = fn(self._shape, frozenset())
        if self._shape is None or self._shape.isNull():
            raise RuntimeError(f"feature '{name}' left no solid")

    def rebuild(self, skip=()):
        """Shape with the named features left out (and features that depend on them)."""
        skip = frozenset(skip)
        s = None
        for name, fn in self.ops:
            if name not in skip:
                s = fn(s, skip)
        return s

    @staticmethod
    def _bool(shape, tool, kind):
        if kind == "add":
            out = tool if shape is None else shape.fuse(tool)
        else:
            if shape is None:
                raise RuntimeError("cut before any material")
            out = shape.cut(tool)
        return out.removeSplitter()

    def _span(self):
        b = self._shape.BoundBox if self._shape is not None else None
        return 2 * (b.DiagonalLength if b else 0) + 1000

    def _prism(self, profiles, at, axis, start, length):
        sk = Sketch(axis, at)
        for p in profiles:
            p(sk)
        f = _face(sk)
        n = sk.normal
        if start:
            f.translate(n * start)
        solid = f.extrude(n * length)
        if not solid.isValid():
            raise RuntimeError("invalid extrusion")
        return solid

    # -- features
    def extrude(self, name, profiles, depth, z=0.0, down=False, axis="z"):
        """Add material: profiles on the plane at offset z along `axis`, extruded `depth`
        toward +axis (or -axis with down=True)."""
        tool = self._prism(profiles, z, axis, 0, -depth if down else depth)
        self.tools[name] = ("add", tool)
        self._add_op(name, lambda s, skip: self._bool(s, tool, "add"))

    def cut(self, name, profiles, depth=None, z=0.0, down=True, axis="z"):
        """Remove material toward -axis (default) or +axis; depth=None cuts through all both ways."""
        if depth is None:
            L = self._span()
            tool = self._prism(profiles, z, axis, -L, 2 * L)
        else:
            tool = self._prism(profiles, z, axis, 0, -depth if down else depth)
        self.tools[name] = ("cut", tool)
        self._add_op(name, lambda s, skip: self._bool(s, tool, "cut"))

    def sweep(self, name, d, segments, at=0.0, axis="x"):
        """Solid round bar of diameter d along an open path drawn on the plane at offset `at`."""
        sk = Sketch(axis, at)
        path(segments)(sk)
        spine = OCC.Wire(OCC.__sortEdges__(sk.edges))
        e0 = spine.OrderedEdges[0]
        p0 = e0.valueAt(e0.FirstParameter)
        t0 = e0.tangentAt(e0.FirstParameter)
        if p0.distanceToPoint(spine.OrderedVertexes[0].Point) > EPS:
            t0 = -t0
        prof = OCC.Wire([OCC.Circle(p0, t0, d / 2).toShape()])
        tool = spine.makePipeShell([prof], True, True)
        if not tool.isValid() or tool.Volume <= 0:
            raise RuntimeError(f"sweep '{name}' failed")
        self.tools[name] = ("add", tool)
        self._add_op(name, lambda s, skip: self._bool(s, tool, "add"))

    @staticmethod
    def _faces_at(shape, points):
        out = []
        for p in points:
            v = OCC.Vertex(V(*p))
            out.append(min(shape.Faces, key=lambda f: f.distToShape(v)[0]))
        return out

    def shell(self, name, thickness, open_face_points=()):
        """Hollow the body inward, removing the faces found at the given (x, y, z) points.
        No points: a closed hollow body (the inward offset is cut out)."""
        pts = list(open_face_points)

        def fn(s, skip):
            if pts:
                out = s.makeThickness(self._faces_at(s, pts), -thickness, 1e-3)
            else:
                out = s.cut(s.makeOffsetShape(-thickness, 1e-3, join=2))
            if not out.isValid():
                raise RuntimeError(f"shell '{name}' failed")
            return out
        self._add_op(name, fn)

    def fillet(self, name, radius, edge_points, kind="EDGE"):
        """Constant-radius fillet on the edges nearest the points (kind="EDGE"), or on all edges
        of the faces nearest them (kind="FACE")."""
        pts = list(edge_points)

        def fn(s, skip):
            if kind == "FACE":
                edges = [e for f in self._faces_at(s, pts) for e in f.Edges]
            else:
                edges = [min(s.Edges, key=lambda e: e.distToShape(OCC.Vertex(V(*p)))[0]) for p in pts]
            uniq = []
            for e in edges:
                if not any(e.isSame(u) for u in uniq):
                    uniq.append(e)
            out = s.makeFillet(radius, uniq)
            if not out.isValid():
                raise RuntimeError(f"fillet '{name}' failed")
            return out
        self._add_op(name, fn)

    def circular_pattern(self, name, features, count):
        """Repeat the named features `count` times, equally spaced over 360 deg about Z."""
        feats = list(features)
        seeds = [self.tools[f] for f in feats]

        def fn(s, skip):
            if all(f in skip for f in feats):
                return s
            for f, (kind, tool) in zip(feats, seeds):
                if f in skip:
                    continue
                copies = [tool.copy().rotate(V(0, 0, 0), V(0, 0, 1), 360.0 * k / count) for k in range(1, count)]
                s = self._bool(s, OCC.makeCompound(copies), kind)
            return s
        self._add_op(name, fn)

    def render(self, out_dir, views=("isometric", "top", "front", "right")):
        return []

    def link(self, params, dims):
        """Record the parameters; the native file keeps them in a spreadsheet."""
        self.params.update(params)
        self.dims.update(dims)

    # -- native file
    def save(self, path, label):
        doc = App.newDocument("fclib_save", hidden=True)
        try:
            body = doc.addObject("Part::Feature", "Body")
            body.Label, body.Shape = label, self._shape
            if self.params:
                sheet = doc.addObject("Spreadsheet::Sheet", "Params")
                for i, (k, v) in enumerate(sorted(self.params.items()), start=1):
                    sheet.set(f"A{i}", k)
                    sheet.set(f"B{i}", str(v))
                    try:
                        sheet.setAlias(f"B{i}", k)
                    except Exception:  # noqa: BLE001  (alias names can't be unit names such as mm)
                        pass
            doc.recompute()
            doc.saveAs(str(path))
        finally:
            App.closeDocument(doc.Name)
