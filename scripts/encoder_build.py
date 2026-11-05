"""Panel-mount rotary encoder (EC11 / PEC11R style), no PCB.

Axes: body centred on the origin in x/y, z along the shaft, z = 0 at the body
bottom. Pins and tabs go down from z = 0. The shaft has a D-flat on +x.

params.json keys: body {l, w, h}; bushing {d, h}; shaft {d, len (from the body
top)}; flat {depth (from the shaft edge), len}; pins {n_enc, n_sw, pitch, w, t,
len, inset}; tabs {w, t, len, inset}.
"""
import math

from swlib import Part, circle, rect


def geometry(p):
    b, bu, s, fl, pn, tb = p["body"], p["bushing"], p["shaft"], p["flat"], p["pins"], p["tabs"]
    disc = lambda d: math.pi * d * d / 4  # noqa: E731
    z_bu, z_sh = b["h"], b["h"] + bu["h"]
    z_top = b["h"] + s["len"]
    r = s["d"] / 2
    dd = r - fl["depth"]                    # distance of the flat from the axis
    seg = r * r * math.acos(dd / r) - dd * math.sqrt(r * r - dd * dd)
    yp = b["w"] / 2 - pn["inset"]
    enc = [rect((i - (pn["n_enc"] - 1) / 2) * pn["pitch"], -yp, pn["w"], pn["t"]) for i in range(pn["n_enc"])]
    sw = [rect((i - (pn["n_sw"] - 1) / 2) * pn["pitch"] * 2, yp, pn["w"], pn["t"]) for i in range(pn["n_sw"])]
    xt = b["l"] / 2 - tb["inset"]
    tabs = [rect(sx * xt, 0, tb["t"], tb["w"]) for sx in (-1, 1)]
    n_pins = pn["n_enc"] + pn["n_sw"]
    return [
        ("Body", "add", [rect(0, 0, b["l"], b["w"])], 0, b["h"], b["l"] * b["w"] * b["h"]),
        ("Bushing", "add", [circle(0, 0, bu["d"])], z_bu, bu["h"], disc(bu["d"]) * bu["h"]),
        ("Shaft", "add", [circle(0, 0, s["d"])], z_sh, z_top - z_sh, disc(s["d"]) * (z_top - z_sh)),
        ("Pins", "under", enc + sw, 0, pn["len"], n_pins * pn["w"] * pn["t"] * pn["len"]),
        ("Tabs", "under", tabs, 0, tb["len"], 2 * tb["w"] * tb["t"] * tb["len"]),
        # D-flat: the rect overhangs the shaft, so only the circular segment is removed
        ("D_flat", "cut", [rect(dd + 2.0, 0, 4.0, s["d"] + 2.0)], z_top, fl["len"], -seg * fl["len"]),
    ]


def expected(p):
    vol = sum(g[5] for g in geometry(p))
    b = p["body"]
    zmin = -max(p["pins"]["len"], p["tabs"]["len"])
    return round(vol, 3), [b["l"], b["w"], round(b["h"] + p["shaft"]["len"] - zmin, 3)]


def build(app, p):
    part = Part(app)
    try:
        for name, op, profs, z0, h, _ in geometry(p):
            if op == "add":
                part.extrude(name, profs, h, z=z0)
            elif op == "under":
                part.extrude(name, profs, h, z=z0, down=True)
            else:
                part.cut(name, profs, depth=h, z=z0, down=True)
    finally:
        part.close_prefs()
    return part.doc


if __name__ == "__main__":
    import json
    import pathlib
    import sys
    prm = json.loads((pathlib.Path(sys.argv[1]) / "parameters" / "params.json").read_text())
    print(expected(prm))
