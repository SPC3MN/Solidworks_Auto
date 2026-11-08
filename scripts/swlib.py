"""Reusable SolidWorks feature helpers for model scripts. All inputs are in mm.

Coordinate convention: the base sketch plane is the Front Plane (model XY),
height runs along +Z. Sketches on planes offset from Front use the same X/Y,
so profile coordinates are model coordinates.

Every dimension a helper creates is linked to a global variable when the
caller passes `params` names, so GUI edits rebuild correctly (see sw_params.py).
"""
import math
import time

try:  # Windows + pywin32; without them the profile helpers still import (generators' expected())
    import pythoncom
    import win32com.client
    from win32com.client import VARIANT

    NOTHING = VARIANT(pythoncom.VT_DISPATCH, None)
except ImportError:
    pythoncom = win32com = VARIANT = NOTHING = None
MM = 0.001
SW_DEFAULT_TEMPLATE_PART = 8
SW_INPUT_DIM_VAL_ON_CREATE = 10
END_BLIND, END_THROUGH_ALL = 0, 1


def connect():
    try:
        return win32com.client.GetActiveObject("SldWorks.Application")
    except pythoncom.com_error:
        app = win32com.client.Dispatch("SldWorks.Application")
        app.Visible = True
        return app


# ---------------------------------------------------------------- profiles
# A profile is a callable that draws closed geometry into the active sketch.
# Profile coordinates are MODEL coordinates on the sketch plane: (x, y) for
# axis="z" planes and (x, z) for axis="y" planes. _TF maps them to sketch
# coordinates (in metres); _TF_SIGN is -1 when that map mirrors (arcs flip).
_TF = [lambda a, b: (a * MM, b * MM)]
_TF_SIGN = [1]

# Sketch-space map per plane family (verified via bounding boxes, see findings doc).
PLANE_FAMILIES = {
    "z": ("Front Plane", lambda a, b: (a * MM, b * MM), 1),   # (x, y) -> sketch (x, y)
    "y": ("Top Plane", lambda a, b: (a * MM, -b * MM), -1),   # (x, z) -> sketch (x, -z)
    "x": ("Right Plane", lambda a, b: (-b * MM, a * MM), 1),  # (y, z) -> sketch (-z, y), extrude +X
}


def _p(a, b):
    return _TF[0](a, b)


def rect(cx, cy, w, h, r=0.0):
    """Rectangle centred at (cx, cy), optional corner radius r (drawn in the sketch)."""
    def draw(sm):
        x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
        if r <= 0:
            (ax, ay), (bx, by) = _p(x0, y0), _p(x1, y1)
            sm.CreateCornerRectangle(ax, ay, 0, bx, by, 0)
            return
        for (xa, ya), (xb, yb) in (((x0 + r, y0), (x1 - r, y0)), ((x1, y0 + r), (x1, y1 - r)),
                                   ((x1 - r, y1), (x0 + r, y1)), ((x0, y1 - r), (x0, y0 + r))):
            (a1, b1), (a2, b2) = _p(xa, ya), _p(xb, yb)
            sm.CreateLine(a1, b1, 0, a2, b2, 0)
        for c, s, e in (
            ((x1 - r, y0 + r), (x1 - r, y0), (x1, y0 + r)),
            ((x1 - r, y1 - r), (x1, y1 - r), (x1 - r, y1)),
            ((x0 + r, y1 - r), (x0 + r, y1), (x0, y1 - r)),
            ((x0 + r, y0 + r), (x0, y0 + r), (x0 + r, y0)),
        ):
            (ca, cb), (sa, sb), (ea, eb) = _p(*c), _p(*s), _p(*e)
            sm.CreateArc(ca, cb, 0, sa, sb, 0, ea, eb, 0, _TF_SIGN[0])  # 1 = counter-clockwise
    return draw


def circle(cx, cy, d):
    def draw(sm):
        a, b = _p(cx, cy)
        sm.CreateCircleByRadius(a, b, 0, d / 2 * MM)
    return draw


def polygon(points):
    """Closed polyline through [(x, y), ...]."""
    def draw(sm):
        pts = [_p(*q) for q in list(points) + [points[0]]]
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            sm.CreateLine(xa, ya, 0, xb, yb, 0)
    return draw


def slot(cx, cy, length, width, angle_deg=0.0):
    """Straight slot (stadium), overall length `length`, centred at (cx, cy)."""
    def draw(sm):
        a = math.radians(angle_deg)
        half = (length - width) / 2
        dx, dy = half * math.cos(a), half * math.sin(a)
        (a1, b1), (a2, b2) = _p(cx - dx, cy - dy), _p(cx + dx, cy + dy)
        sm.CreateSketchSlot(0, 0, width * MM, a1, b1, 0, a2, b2, 0, 0, 0, 0, 1, False)
    return draw


def path(segments):
    """Open sketch path for a sweep: ["line", (a, b), (a, b)] or ["arc", centre, start, end]
    (arcs under 180 degrees; direction worked out from the points)."""
    def draw(sm):
        for seg in segments:
            if seg[0] == "line":
                (a1, b1), (a2, b2) = _p(*seg[1]), _p(*seg[2])
                sm.CreateLine(a1, b1, 0, a2, b2, 0)
            else:
                (ca, cb), (sa, sb), (ea, eb) = (_p(*q) for q in seg[1:])
                ccw = (sa - ca) * (eb - cb) - (sb - cb) * (ea - ca) > 0
                sm.CreateArc(ca, cb, 0, sa, sb, 0, ea, eb, 0, 1 if ccw else -1)
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


# ---------------------------------------------------------------- render

# SolidWorks' named views assume +Y is up; our models use +Z as height, so build
# Z-up views ourselves. Each is (screen-right, screen-up, toward-viewer) in model axes.
_S2, _S3, _S6 = math.sqrt(2), math.sqrt(3), math.sqrt(6)
Z_UP_VIEWS = {
    "isometric": ((1 / _S2, 1 / _S2, 0), (-1 / _S6, 1 / _S6, 2 / _S6), (1 / _S3, -1 / _S3, 1 / _S3)),
    "top": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    "front": ((1, 0, 0), (0, 0, 1), (0, -1, 0)),
    "right": ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
}


def _invoke(obj, name, *args):
    """Call a COM method explicitly (late binding mistakes some for properties)."""
    o = obj._oleobj_
    return o.Invoke(o.GetIDsOfNames(name), 0, pythoncom.DISPATCH_METHOD, 1, *args)


def render(doc, out_dir, views=("isometric", "top", "front", "right"), size=None):
    """Save shaded PNGs of Z-up views (zoomed to fit). Returns the written paths."""
    import pathlib
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    app = win32com.client.GetActiveObject("SldWorks.Application")
    mu = app.GetMathUtility
    # Hide reference planes: they show in renders and zoom-to-fit frames them, not the part.
    f = doc.FirstFeature
    while f is not None:
        if f.GetTypeName2 == "RefPlane":
            doc.ClearSelection2(True)
            f.Select2(False, 0)
            _invoke(doc, "BlankRefGeom")
        f = f.GetNextFeature
    doc.ClearSelection2(True)
    written = []
    for name in views:
        r, u, d = Z_UP_VIEWS[name]
        m = [r[0], u[0], d[0], r[1], u[1], d[1], r[2], u[2], d[2]]  # column-major (verified)
        t = win32com.client.Dispatch(_invoke(
            mu, "CreateTransform", VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, m + [0.0, 0, 0, 1, 0, 0, 0])))
        doc.ActiveView.Orientation3 = t
        _invoke(doc, "ViewZoomtofit2")  # property-style access does not run it
        _invoke(doc, "GraphicsRedraw2")
        png = out_dir / f"{name}.png"
        e = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        w = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        if doc.Extension.SaveAs3(str(png), 0, 1, NOTHING, NOTHING, e, w) and png.exists():
            written.append(png)
    return written


# ---------------------------------------------------------------- part

class Part:
    def __init__(self, app=None):
        self.app = app or connect()
        self._prev = self.app.GetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE)
        self.app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, False)
        tpl = self.app.GetUserPreferenceStringValue(SW_DEFAULT_TEMPLATE_PART)
        self.doc = self.app.NewDocument(tpl, 0, 0, 0)
        if self.doc is None:
            raise RuntimeError(f"NewDocument failed ({tpl})")
        # A freshly created document occasionally isn't ready yet (its managers
        # aren't reachable for a moment); wait briefly and retry.
        for attempt in range(10):
            try:
                self.fm, self.sm, self.ext = self.doc.FeatureManager, self.doc.SketchManager, self.doc.Extension
                break
            except AttributeError:
                if attempt == 9:
                    raise
                time.sleep(0.5)
        self._planes = {("z", 0.0): "Front Plane", ("y", 0.0): "Top Plane", ("x", 0.0): "Right Plane"}
        self._last_sketch = None

    def close_prefs(self):
        self.app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, self._prev)

    # -- planes
    def plane_at(self, at, axis="z"):
        """Name of a plane normal to `axis` at offset `at` (mm), creating it if needed.
        axis="z": parallel to Front Plane; axis="y": parallel to Top Plane."""
        key = (axis, round(float(at), 6))
        if key in self._planes:
            return self._planes[key]
        self.doc.ClearSelection2(True)
        self.ext.SelectByID2(PLANE_FAMILIES[axis][0], "PLANE", 0, 0, 0, False, 0, NOTHING, 0)
        # 8 = swRefPlaneReferenceConstraint_Distance; +256 (_OptionFlip) for negative offsets.
        flags = 8 | (256 if at < 0 else 0)
        plane = self.fm.InsertRefPlane(flags, abs(at) * MM, 0, 0, 0, 0)
        if plane is None:
            raise RuntimeError(f"could not create plane {axis}={at}")
        plane.Name = f"Plane_{axis}{at:g}".replace(".", "_").replace("-", "m")
        self._planes[key] = plane.Name
        return plane.Name

    def _sketch(self, at, profiles, axis="z"):
        self.doc.ClearSelection2(True)
        self.ext.SelectByID2(self.plane_at(at, axis), "PLANE", 0, 0, 0, False, 0, NOTHING, 0)
        self.sm.InsertSketch(True)
        self.sm.AddToDB = True  # no snapping/inference while drawing
        _, _TF[0], _TF_SIGN[0] = PLANE_FAMILIES[axis]
        try:
            for p in profiles:
                p(self.sm)
        finally:
            _, _TF[0], _TF_SIGN[0] = PLANE_FAMILIES["z"]
        self.sm.AddToDB = False
        self.sm.InsertSketch(True)
        self._last_sketch = self.doc.FeatureByPositionReverse(0)
        self._select_sketch()

    def _select_sketch(self):
        """Select exactly the sketch just drawn, so the feature can't pick up a stale selection."""
        self.doc.ClearSelection2(True)
        if self._last_sketch is not None:
            self._last_sketch.Select2(False, 0)

    def _feature(self, make):
        """Run a feature call; if SolidWorks returns nothing, reselect the sketch and retry once."""
        f = make()
        if f is None:
            time.sleep(0.3)
            self._select_sketch()
            f = make()
        return f

    def _name(self, feat, name, what):
        if feat is None:
            raise RuntimeError(f"{what} '{name}' failed")
        feat.Name = name
        return feat

    # -- features
    def extrude(self, name, profiles, depth, z=0.0, down=False, axis="z"):
        """Add material: sketch on the plane at offset z along `axis`, extrude `depth`
        toward +axis (or -axis with down=True)."""
        self._sketch(z, profiles, axis)
        # FeatureExtrusion3 args: Sd, Flip, Dir (reverse direction), T1, T2, D1, ...
        f = self._feature(lambda: self.fm.FeatureExtrusion3(
            True, False, down, END_BLIND, 0, depth * MM, 0, False, False, False, False,
            0, 0, False, False, False, False, True, True, True, 0, 0, False))
        return self._name(f, name, "extrude")

    def sweep(self, name, d, segments, at=0.0, axis="x"):
        """Solid round bar of diameter d along an open path (see path()) drawn on the plane
        at offset `at` normal to `axis`. Uses the built-in circular profile, so no profile sketch."""
        self._sketch(at, [path(segments)], axis)
        self.doc.ClearSelection2(True)
        self._last_sketch.Select2(False, 4)  # mark 4 = sweep path
        f = self.fm.InsertProtrusionSwept4(False, False, 0, False, False, 0, 0, False, 0, 0, 0, 0,
                                           True, True, True, 0, True, True, d * MM, 0)
        return self._name(f, name, "sweep")

    def cut(self, name, profiles, depth=None, z=0.0, down=True, axis="z"):
        """Remove material: sketch on the plane at offset z along `axis`, cut `depth`
        toward -axis (default) or +axis. depth=None cuts through everything both ways."""
        # FeatureCut4 args: Sd, Flip (= cut OUTSIDE the profile, keep False), Dir (reverse
        # direction), T1, T2, D1, D2, ... Through-all cuts go both ways so the side doesn't matter.
        self._sketch(z, profiles, axis)
        if depth is None:
            sd, rev, t1, t2, d1 = False, False, END_THROUGH_ALL, END_THROUGH_ALL, 0
        else:
            # Blind cuts default to going AGAINST the plane normal (opposite to
            # extrudes; verified with a probe), so "down" means Dir = False.
            sd, rev, t1, t2, d1 = True, not down, END_BLIND, 0, depth * MM
        f = self._feature(lambda: self.fm.FeatureCut4(
            sd, False, rev, t1, t2, d1, 0, False, False, False, False,
            0, 0, False, False, False, False, False, True, True, False, False, False,
            0, 0, False, False))
        return self._name(f, name, "cut")

    def shell(self, name, thickness, open_face_points=()):
        """Hollow the body. open_face_points: [(x, y, z) mm] points lying on faces to remove."""
        self.doc.ClearSelection2(True)
        for i, (x, y, z) in enumerate(open_face_points):
            self.ext.SelectByID2("", "FACE", x * MM, y * MM, z * MM, i > 0, 0, NOTHING, 0)
        self.doc.InsertFeatureShell(thickness * MM, False)  # lives on ModelDoc2, not FeatureManager
        f = self.doc.FeatureByPositionReverse(0)
        if f is None or f.GetTypeName2 != "Shell":
            raise RuntimeError(f"shell '{name}' failed")
        f.Name = name
        return f

    def fillet(self, name, radius, edge_points, kind="EDGE"):
        """Constant-radius fillet on the edges (kind="EDGE") or on all edges of the faces
        (kind="FACE") found at the given (x, y, z) mm points. Face picks are more reliable for
        small features: a face is a bigger target than its edge."""
        self.doc.ClearSelection2(True)
        for i, (x, y, z) in enumerate(edge_points):
            self.ext.SelectByID2("", kind, x * MM, y * MM, z * MM, i > 0, 1, NOTHING, 0)
        f = self.fm.FeatureFillet3(195, radius * MM, 0, 0, 0, 0, 0, NOTHING, NOTHING, NOTHING,
                                   NOTHING, NOTHING, NOTHING, NOTHING)
        return self._name(f, name, "fillet")

    def z_axis(self):
        """Reference axis along model Z (Top Plane x Right Plane), created once."""
        if getattr(self, "_zaxis", None):
            return self._zaxis
        self.doc.ClearSelection2(True)
        self.ext.SelectByID2("Top Plane", "PLANE", 0, 0, 0, False, 0, NOTHING, 0)
        self.ext.SelectByID2("Right Plane", "PLANE", 0, 0, 0, True, 0, NOTHING, 0)
        self.doc.InsertAxis2(True)
        f = self.doc.FeatureByPositionReverse(0)
        if f is None or f.GetTypeName2 != "RefAxis":
            raise RuntimeError("could not create the Z axis")
        f.Name = "Axis_Z"
        self._zaxis = f.Name
        return f.Name

    def circular_pattern(self, name, features, count):
        """Pattern the named features `count` times, equally spaced over 360 deg about Z."""
        ax = self.z_axis()
        self.doc.ClearSelection2(True)
        self.ext.SelectByID2(ax, "AXIS", 0, 0, 0, False, 1, NOTHING, 0)
        for fn in features:
            self.ext.SelectByID2(fn, "BODYFEATURE", 0, 0, 0, True, 4, NOTHING, 0)
        # Number, Spacing (rad), Flip, DName, GeometryPattern, EqualSpacing, VaryInstance
        f = self.fm.FeatureCircularPattern4(count, 2 * math.pi, False, "NULL", True, True, False)
        return self._name(f, name, "circular pattern")

    def render(self, out_dir, views=("isometric", "top", "front", "right")):
        return render(self.doc, out_dir, views)

    def link(self, params, dims):
        """Create global variables for params and link {dim_full_name: param} to them."""
        eqm = self.doc.GetEquationMgr
        for k, v in params.items():
            eqm.Add2(-1, f'"{k}" = {v}mm', True)
        for dim, k in dims.items():
            eqm.Add2(-1, f'"{dim}" = "{k}"', True)
        self.doc.EditRebuild3
