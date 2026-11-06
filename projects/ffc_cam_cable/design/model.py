"""Camera ribbon (FFC) from the Pi 5 CAM/DISP0 connector to the HQ camera, in
Pi 5 board coordinates. The cable's path runs in the x-z plane. It is drawn as
one mitred thick-polyline profile on a Y-normal plane and extruded across the
cable width, so the volume is exactly centreline length x thickness x width."""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts"))
from swlib import Part, polygon  # noqa: E402


def thick_polyline(pts, t):
    """Outline of a polyline of thickness t with mitred joints and square ends."""
    def normal(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy)
        return (-dy / n, dx / n)

    def side(s):
        out = []
        for i, p in enumerate(pts):
            ns = [normal(pts[i - 1], p)] if i > 0 else []
            ns += [normal(p, pts[i + 1])] if i < len(pts) - 1 else []
            mx, my = sum(n[0] for n in ns), sum(n[1] for n in ns)
            m = math.hypot(mx, my)
            mx, my = mx / m, my / m
            k = (t / 2) / (mx * ns[0][0] + my * ns[0][1])  # miter length
            out.append((p[0] + s * k * mx, p[1] + s * k * my))
        return out
    return side(1) + side(-1)[::-1]


def length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def build(app, p):
    part = Part(app)
    try:
        path = [tuple(q) for q in p["path_xz"]]
        part.extrude("Ribbon", [polygon(thick_polyline(path, p["t"]))], p["w"], z=p["y0"], axis="y")
    finally:
        part.close_prefs()
    return part.doc


if __name__ == "__main__":
    import json
    prm = json.loads((pathlib.Path(__file__).parents[1] / "parameters" / "params.json").read_text())
    L = length(prm["path_xz"])
    print("length", L, "volume", L * prm["t"] * prm["w"])
