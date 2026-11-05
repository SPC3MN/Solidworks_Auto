"""Reusable SolidWorks feature helpers for model scripts. All inputs are in mm.

Coordinate convention: the base sketch plane is the Front Plane (model XY),
height runs along +Z. Sketches on planes offset from Front use the same X/Y,
so profile coordinates are model coordinates.

Every dimension a helper creates is linked to a global variable when the
caller passes `params` names, so GUI edits rebuild correctly (see sw_params.py).
"""
import math

import pythoncom
import win32com.client
from win32com.client import VARIANT

NOTHING = VARIANT(pythoncom.VT_DISPATCH, None)
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

def rect(cx, cy, w, h, r=0.0):
    """Rectangle centred at (cx, cy), optional corner radius r (drawn in the sketch)."""
    def draw(sm):
        x0, x1, y0, y1 = (cx - w / 2) * MM, (cx + w / 2) * MM, (cy - h / 2) * MM, (cy + h / 2) * MM
        if r <= 0:
            sm.CreateCornerRectangle(x0, y0, 0, x1, y1, 0)
            return
        rr = r * MM
        sm.CreateLine(x0 + rr, y0, 0, x1 - rr, y0, 0)
        sm.CreateLine(x1, y0 + rr, 0, x1, y1 - rr, 0)
        sm.CreateLine(x1 - rr, y1, 0, x0 + rr, y1, 0)
        sm.CreateLine(x0, y1 - rr, 0, x0, y0 + rr, 0)
        for (ax, ay), (sx, sy), (ex, ey) in (
            ((x1 - rr, y0 + rr), (x1 - rr, y0), (x1, y0 + rr)),
            ((x1 - rr, y1 - rr), (x1, y1 - rr), (x1 - rr, y1)),
            ((x0 + rr, y1 - rr), (x0 + rr, y1), (x0, y1 - rr)),
            ((x0 + rr, y0 + rr), (x0, y0 + rr), (x0 + rr, y0)),
        ):
            sm.CreateArc(ax, ay, 0, sx, sy, 0, ex, ey, 0, 1)  # 1 = counter-clockwise
    return draw


def circle(cx, cy, d):
    def draw(sm):
        sm.CreateCircleByRadius(cx * MM, cy * MM, 0, d / 2 * MM)
    return draw


def polygon(points):
    """Closed polyline through [(x, y), ...]."""
    def draw(sm):
        pts = list(points) + [points[0]]
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            sm.CreateLine(xa * MM, ya * MM, 0, xb * MM, yb * MM, 0)
    return draw


def slot(cx, cy, length, width, angle_deg=0.0):
    """Straight slot (stadium), overall length `length`, centred at (cx, cy)."""
    def draw(sm):
        a = math.radians(angle_deg)
        half = (length - width) / 2
        dx, dy = half * math.cos(a), half * math.sin(a)
        sm.CreateSketchSlot(0, 0, width * MM,
                            (cx - dx) * MM, (cy - dy) * MM, 0,
                            (cx + dx) * MM, (cy + dy) * MM, 0, 0, 0, 0, 1, False)
    return draw


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
    written = []
    for name in views:
        r, u, d = Z_UP_VIEWS[name]
        m = [r[0], u[0], d[0], r[1], u[1], d[1], r[2], u[2], d[2]]  # column-major (verified)
        t = win32com.client.Dispatch(_invoke(
            mu, "CreateTransform", VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, m + [0.0, 0, 0, 1, 0, 0, 0])))
        doc.ActiveView.Orientation3 = t
        doc.ViewZoomtofit2
        doc.GraphicsRedraw2
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
        self.fm, self.sm, self.ext = self.doc.FeatureManager, self.doc.SketchManager, self.doc.Extension
        self._planes = {0.0: "Front Plane"}

    def close_prefs(self):
        self.app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, self._prev)

    # -- planes
    def plane_at(self, z):
        """Name of a plane parallel to Front at height z (mm), creating it if needed."""
        z = round(float(z), 6)
        if z in self._planes:
            return self._planes[z]
        self.doc.ClearSelection2(True)
        self.ext.SelectByID2("Front Plane", "PLANE", 0, 0, 0, False, 0, NOTHING, 0)
        # 8 = swRefPlaneReferenceConstraint_Distance; 264 adds _OptionFlip for negative z.
        flags = 8 | (256 if z < 0 else 0)
        plane = self.fm.InsertRefPlane(flags, abs(z) * MM, 0, 0, 0, 0)
        if plane is None:
            raise RuntimeError(f"could not create plane at z={z}")
        plane.Name = f"Plane_z{z:g}".replace(".", "_").replace("-", "m")
        self._planes[z] = plane.Name
        return plane.Name

    def _sketch(self, z, profiles):
        self.doc.ClearSelection2(True)
        self.ext.SelectByID2(self.plane_at(z), "PLANE", 0, 0, 0, False, 0, NOTHING, 0)
        self.sm.InsertSketch(True)
        self.sm.AddToDB = True  # no snapping/inference while drawing
        for p in profiles:
            p(self.sm)
        self.sm.AddToDB = False
        self.sm.InsertSketch(True)

    def _name(self, feat, name, what):
        if feat is None:
            raise RuntimeError(f"{what} '{name}' failed")
        feat.Name = name
        return feat

    # -- features
    def extrude(self, name, profiles, depth, z=0.0, down=False):
        """Add material: sketch at height z, extrude `depth` up (or down)."""
        self._sketch(z, profiles)
        f = self.fm.FeatureExtrusion3(
            True, down, False, END_BLIND, 0, depth * MM, 0, False, False, False, False,
            0, 0, False, False, False, False, True, True, True, 0, 0, False)
        return self._name(f, name, "extrude")

    def cut(self, name, profiles, depth=None, z=0.0, down=True):
        """Remove material: sketch at height z, cut `depth` down (default) or up.
        depth=None cuts through everything in that direction."""
        # FeatureCut4 args: Sd, Flip (= cut OUTSIDE the profile, keep False), Dir (reverse
        # direction), T1, T2, D1, D2, ... Through-all cuts go both ways so the side doesn't matter.
        self._sketch(z, profiles)
        if depth is None:
            sd, rev, t1, t2, d1 = False, False, END_THROUGH_ALL, END_THROUGH_ALL, 0
        else:
            sd, rev, t1, t2, d1 = True, down, END_BLIND, 0, depth * MM
        f = self.fm.FeatureCut4(
            sd, False, rev, t1, t2, d1, 0, False, False, False, False,
            0, 0, False, False, False, False, False, True, True, False, False, False,
            0, 0, False, False)
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

    def fillet(self, name, radius, edge_points):
        """Constant-radius fillet on edges found at the given (x, y, z) mm points."""
        self.doc.ClearSelection2(True)
        for i, (x, y, z) in enumerate(edge_points):
            self.ext.SelectByID2("", "EDGE", x * MM, y * MM, z * MM, i > 0, 1, NOTHING, 0)
        f = self.fm.FeatureFillet3(195, radius * MM, 0, 0, 0, 0, 0, NOTHING, NOTHING, NOTHING,
                                   NOTHING, NOTHING, NOTHING, NOTHING)
        return self._name(f, name, "fillet")

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
