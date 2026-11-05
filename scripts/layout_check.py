"""Check a pixel-based component layout before building: converts it to mm,
reports parts that overlap or sit closer than `gap` to each other or to keep-out
boxes, and prints the summed component volume for the requirements.

Usage: .venv\\Scripts\\python scripts\\layout_check.py projects\\rpi_dac_pro
"""
import itertools
import json
import math
import pathlib
import sys


def to_mm(m, px, py):
    return (m["x0_mm"] + (px - m["x0_px"]) * m["sx"], m["y0_mm"] + (m["y0_px"] - py) * m["sy"])


def boxes(lay):
    """[(ref, x0, y0, x1, y1, height)] for parts, circles approximated by their square."""
    m, out = lay["px_to_mm"], []
    for c in lay["parts"]:
        k = lay["packages"][c["pkg"]]
        l, w = (k["w"], k["l"]) if c.get("rot") == 90 else (k["l"], k["w"])
        x, y = to_mm(m, c["px"], c["py"])
        out.append((c["ref"], x - l / 2, y - w / 2, x + l / 2, y + w / 2, k["h"], "box"))
    for g in lay["pads"]:
        for px in g["px"]:
            for py in g["py"]:
                x, y = to_mm(m, px, py)
                r = g["d"] / 2
                out.append((g["ref"], x - r, y - r, x + r, y + r, lay["pad_h"], "disc"))
    return out


def volume(b):
    _, x0, y0, x1, y1, h, kind = b
    return math.pi * ((x1 - x0) / 2) ** 2 * h if kind == "disc" else (x1 - x0) * (y1 - y0) * h


def clearance(a, b):
    dx = max(b[1] - a[3], a[1] - b[3], 0)
    dy = max(b[2] - a[4], a[2] - b[4], 0)
    if dx == 0 and dy == 0:
        return -1.0  # overlap
    return math.hypot(dx, dy)


def main(project, gap=0.15):
    lay = json.loads((project / "parameters" / "layout.json").read_text())
    keepouts = json.loads((project / "parameters" / "keepouts.json").read_text()) \
        if (project / "parameters" / "keepouts.json").exists() else []
    bs = boxes(lay)
    ko = [(k["ref"], k["x0"], k["y0"], k["x1"], k["y1"], 0, "box") for k in keepouts]
    bad = []
    for a, b in itertools.combinations(bs, 2):
        if a[0] == b[0] and a[6] == "disc":
            continue  # pads of one group are spaced by design
        c = clearance(a, b)
        if c < gap:
            bad.append((a[0], b[0], round(c, 3)))
    for a in bs:
        for k in ko:
            c = clearance(a, k)
            if c < gap:
                bad.append((a[0], k[0], round(c, 3)))
    for a in bs:
        if a[1] < 0.3 or a[2] < 0.3 or a[3] > 64.7 or a[4] > 56.2:
            bad.append((a[0], "board edge", None))
    total = sum(volume(b) for b in bs)
    print(f"{len(bs)} items, component volume {total:.3f} mm^3")
    for x in bad:
        print("CONFLICT", x)
    return bad, total


if __name__ == "__main__":
    bad, _ = main(pathlib.Path(sys.argv[1]))
    sys.exit(1 if bad else 0)
