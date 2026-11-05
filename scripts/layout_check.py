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


def part_geom(lay, c):
    """(x, y, l, w, h, rot) in mm for one part entry. Entries give either a 'pkg'
    or explicit l/w/h, and either photo px/py or board x/y."""
    k = lay.get("packages", {}).get(c.get("pkg"), c)
    l, w, h = k["l"], k["w"], c.get("h", k["h"])
    rot = c.get("rot", 0)
    if rot == 90:
        l, w = w, l
    x, y = (c["x"], c["y"]) if "x" in c else to_mm(lay["px_to_mm"], c["px"], c["py"])
    return x, y, l, w, h, rot


LEAD_MARGIN = {"sot23": 0.5, "sod323": 0.4, "tssop": 0.6, "qfn": 0.25}  # detail beyond the body


def kind_of(lay, c):
    return c.get("kind") or lay.get("packages", {}).get(c.get("pkg"), {}).get("kind", "plain")


def boxes(lay, with_leads=True):
    """[(ref, x0, y0, x1, y1, height, kind, overhang)]; rotated parts use their bounding square.
    with_leads grows each box by its package's lead/pad reach (for the clearance check)."""
    out = []
    for c in lay["parts"]:
        x, y, l, w, h, rot = part_geom(lay, c)
        if rot == 45:
            hx = hy = (l + w) / 2 / math.sqrt(2)
        else:
            hx, hy = l / 2, w / 2
        if with_leads:
            m = LEAD_MARGIN.get(kind_of(lay, c), 0)
            hx, hy = hx + m, hy + m
        b = (c["ref"], x - hx, y - hy, x + hx, y + hy, h, "box", c.get("overhang", False))
        out.append(b if rot != 45 else b[:6] + ("rot45", b[7], l * w * h))
    m = lay.get("px_to_mm")
    for g in lay.get("pads", []):
        for px in g["px"]:
            for py in g["py"]:
                x, y = to_mm(m, px, py)
                r = g["d"] / 2
                out.append((g["ref"], x - r, y - r, x + r, y + r, lay["pad_h"], "disc", False))
    return out


def volume(b):
    _, x0, y0, x1, y1, h, kind = b[:7]
    if kind == "rot45":
        return b[8]
    return math.pi * ((x1 - x0) / 2) ** 2 * h if kind == "disc" else (x1 - x0) * (y1 - y0) * h


def clearance(a, b):
    dx = max(b[1] - a[3], a[1] - b[3], 0)
    dy = max(b[2] - a[4], a[2] - b[4], 0)
    if dx == 0 and dy == 0:
        return -1.0  # overlap
    return math.hypot(dx, dy)


def main(project, gap=0.15):
    f = project / "parameters" / "layout.json"
    lay = json.loads((f if f.exists() else project / "parameters" / "smd_layout.json").read_text())
    keepouts = json.loads((project / "parameters" / "keepouts.json").read_text()) \
        if (project / "parameters" / "keepouts.json").exists() else []
    bs = boxes(lay)
    ko = [(k["ref"], k["x0"], k["y0"], k["x1"], k["y1"], 0, "box", False) for k in keepouts]
    bl, bw = lay.get("board", {"l": 65, "w": 56.5}).values()
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
        if not a[7] and (a[1] < 0.3 or a[2] < 0.3 or a[3] > bl - 0.3 or a[4] > bw - 0.3):
            bad.append((a[0], "board edge", None))
    total = sum(volume(b) for b in boxes(lay, with_leads=False))
    print(f"{len(bs)} items, plain component volume {total:.3f} mm^3")
    try:
        import details
        ops = details.layout_ops(lay, 1.6)
        pads = sum(volume(b) for b in bs if b[6] == "disc")
        print(f"detailed component volume {details.total_volume(ops) + pads:.3f} mm^3"
              f" ({len(ops)} ops, pads {pads:.3f})")
    except Exception as e:  # noqa: BLE001
        print("detail volume unavailable:", e)
    for x in bad:
        print("CONFLICT", x)
    return bad, total


if __name__ == "__main__":
    bad, _ = main(pathlib.Path(sys.argv[1]))
    sys.exit(1 if bad else 0)
