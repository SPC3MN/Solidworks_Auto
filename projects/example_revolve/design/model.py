"""Kernel probe: a turned knob made with revolve (body), and two revolve cuts (V-groove, bore)."""
import fclib


def build(app, p):
    part = fclib.Part()
    R, r, H = p["flange_d"] / 2, p["stem_d"] / 2, p["height"]
    part.revolve("Body", [fclib.polygon([(0, 0), (R, 0), (R, p["flange_h"]), (r, p["flange_h"]), (r, H), (0, H)])])
    # Cut profiles run 1 mm past the surface they open, so no cut face lies on a body face.
    z, w, g = p["groove_z"], p["groove_w"], p["groove_depth"]
    half = w / 2 * (g + 1) / g
    part.revolve("Groove", [fclib.polygon([(r + 1, z - half), (r - g, z), (r + 1, z + half)])], cut=True)
    b, z0 = p["bore_d"] / 2, H - p["bore_depth"]
    part.revolve("Bore", [fclib.polygon([(0, z0), (b, z0), (b, H + 1), (0, H + 1)])], cut=True)
    part.link(p, {})
    return part.doc
