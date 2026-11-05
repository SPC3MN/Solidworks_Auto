"""Build a populated circuit board from one layout.json (all positions in board mm).

Used by the electronic-component projects (rpi_zero_2w, pcm5102a_dac, ...). Same
conventions as rpi_dac_pro: x along the board's long edge, y = 0 at the edge
where the main connectors exit, z up from the bottom of the PCB. Components are
fused into one solid.

layout.json keys (all optional except "board"):
  board:     {l, w}                             PCB outline
  pcb:       {t, r}                             thickness and corner radius
  holes:     [{x, y, d}]                        mounting holes (cut through)
  thru:      [{x0, y0, cols, rows, pitch, d}]   unpopulated plated holes (cut through)
  headers:   [{x, y, cols, rows, pitch, block_h, pin, pin_h}]  pin headers on top
  packages/parts: as rpi_dac_pro (kinds from scripts/details.py), x/y in mm
  blocks:    [{ref, x, y, l, w, h, z0}]         plain boxes starting at height z0
  cyls:      [{ref, x, y, d, h, z0, bore_d?, bore_depth?}]  vertical cylinders (shafts, mounts);
             the bore is cut down from the top, bore_depth deep (default: all the way)
  side_cyls: [{ref, x, z, d, len, bore_d?}]     cylinders along -y from y = 0 (jack noses)

expected(lay) returns the volume and bounding box of exactly these primitives,
worked out without SolidWorks, for requirements.md and spec.json.
"""
import json
import math
import pathlib

import details
from swlib import Part, circle, rect


def _board(lay):
    # "board" holds only {l, w} because layout_check unpacks exactly those two
    b, p = lay["board"], lay.get("pcb", {})
    return b["l"], b["w"], p.get("t", 1.6), p.get("r", 0)


def _header_geom(h):
    """(block rect, [pin rects]) as (cx, cy, l, w)."""
    p, c, r = h["pitch"], h["cols"], h["rows"]
    block = (h["x"], h["y"], c * p, r * p)
    pins = [(h["x"] + (i - (c - 1) / 2) * p, h["y"] + (j - (r - 1) / 2) * p, h["pin"], h["pin"])
            for i in range(c) for j in range(r)]
    return block, pins


def _thru_points(g):
    return [(g["x0"] + i * g["pitch"], g["y0"] + j * g["pitch"])
            for i in range(g["cols"]) for j in range(g["rows"])]


def build(app, lay):
    L, W, T, R = _board(lay)
    part = Part(app)
    try:
        part.extrude("PCB", [rect(L / 2, W / 2, L, W, R)], T)
        for n, h in enumerate(lay.get("headers", [])):
            block, pins = _header_geom(h)
            part.extrude(f"Header{n}_Block", [rect(*block)], h["block_h"], z=T)
            part.extrude(f"Header{n}_Pins", [rect(*p) for p in pins], h["pin_h"], z=T + h["block_h"])
        ops = details.layout_ops(lay, T)
        details.apply(part, ops, "SMD", "add")
        # Plain blocks and vertical cylinders, grouped by start height and height
        groups = {}
        for b in lay.get("blocks", []):
            groups.setdefault((b["z0"], b["h"]), []).append(rect(b["x"], b["y"], b["l"], b["w"]))
        for c in lay.get("cyls", []):
            groups.setdefault((c["z0"], c["h"]), []).append(circle(c["x"], c["y"], c["d"]))
        for n, ((z0, h), profs) in enumerate(sorted(groups.items())):
            part.extrude(f"Body{n:02d}", profs, h, z=z0)
        for n, s in enumerate(lay.get("side_cyls", [])):
            part.extrude(f"Side{n}_{s['ref']}", [circle(s["x"], s["z"], s["d"])], s["len"],
                         z=0, down=True, axis="y")
        # Cuts
        details.apply(part, ops, "SMD", "cut")
        for n, c in enumerate(c for c in lay.get("cyls", []) if c.get("bore_d")):
            part.cut(f"Bore{n}_{c['ref']}", [circle(c["x"], c["y"], c["bore_d"])],
                     depth=c.get("bore_depth", c["h"]), z=c["z0"] + c["h"], down=True)
        for n, s in enumerate(s for s in lay.get("side_cyls", []) if s.get("bore_d")):
            part.cut(f"SideBore{n}_{s['ref']}", [circle(s["x"], s["z"], s["bore_d"])],
                     depth=s["len"], z=0, down=True, axis="y")
        holes = [circle(h["x"], h["y"], h["d"]) for h in lay.get("holes", [])]
        holes += [circle(x, y, g["d"]) for g in lay.get("thru", []) for x, y in _thru_points(g)]
        if holes:  # through the PCB only, so parts lying over a hole stay whole
            part.cut("Holes", holes, depth=T, z=T, down=True)
        part.link({"pcb_t": T}, {"D1@PCB": "pcb_t"})
    finally:
        part.close_prefs()
    return part.doc


def expected(lay):
    """Volume (mm^3) and bounding box (mm) of the layout's primitives."""
    L, W, T, R = _board(lay)
    disc = lambda d: math.pi * d * d / 4  # noqa: E731
    v = {"pcb": (L * W - (4 - math.pi) * R * R) * T}
    v["holes"] = -sum(disc(h["d"]) * T for h in lay.get("holes", []))
    v["thru"] = -sum(disc(g["d"]) * T * len(_thru_points(g)) for g in lay.get("thru", []))
    v["headers"] = sum(h["cols"] * h["pitch"] * h["rows"] * h["pitch"] * h["block_h"]
                       + h["cols"] * h["rows"] * h["pin"] ** 2 * h["pin_h"] for h in lay.get("headers", []))
    v["parts"] = details.total_volume(details.layout_ops(lay, T))
    v["blocks"] = sum(b["l"] * b["w"] * b["h"] for b in lay.get("blocks", []))
    v["cyls"] = sum(disc(c["d"]) * c["h"] - disc(c.get("bore_d", 0)) * c.get("bore_depth", c["h"])
                    for c in lay.get("cyls", []))
    v["side_cyls"] = sum((disc(s["d"]) - disc(s.get("bore_d", 0))) * s["len"] for s in lay.get("side_cyls", []))
    # Bounding box from every primitive's extent (parts use their footprint and height)
    xs, ys, zs = [0, L], [0, W], [0, T]
    for h in lay.get("headers", []):
        (cx, cy, bl, bw), _ = _header_geom(h)
        xs += [cx - bl / 2, cx + bl / 2]; ys += [cy - bw / 2, cy + bw / 2]; zs.append(T + h["block_h"] + h["pin_h"])
    from layout_check import part_geom
    for c in lay.get("parts", []):
        x, y, l, w, h, rot = part_geom(lay, c)
        xs += [x - l / 2, x + l / 2]; ys += [y - w / 2, y + w / 2]; zs.append(T + h)
    for b in lay.get("blocks", []):
        xs += [b["x"] - b["l"] / 2, b["x"] + b["l"] / 2]; ys += [b["y"] - b["w"] / 2, b["y"] + b["w"] / 2]
        zs += [b["z0"], b["z0"] + b["h"]]
    for c in lay.get("cyls", []):
        xs += [c["x"] - c["d"] / 2, c["x"] + c["d"] / 2]; ys += [c["y"] - c["d"] / 2, c["y"] + c["d"] / 2]
        zs += [c["z0"], c["z0"] + c["h"]]
    for s in lay.get("side_cyls", []):
        xs += [s["x"] - s["d"] / 2, s["x"] + s["d"] / 2]; ys.append(-s["len"]); zs += [s["z"] - s["d"] / 2, s["z"] + s["d"] / 2]
    bbox = [round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3), round(max(zs) - min(zs), 3)]
    return round(sum(v.values()), 3), bbox, {k: round(x, 3) for k, x in v.items()}


def keepouts(lay):
    """Keep-out boxes for layout_check: holes, headers, blocks, cylinders."""
    out = []
    for n, h in enumerate(lay.get("holes", [])):
        r = h["d"] / 2 + 0.3
        out.append({"ref": f"hole{n}", "x0": h["x"] - r, "y0": h["y"] - r, "x1": h["x"] + r, "y1": h["y"] + r})
    for n, g in enumerate(lay.get("thru", [])):
        r = g["d"] / 2 + 0.3
        pts = _thru_points(g)
        out.append({"ref": f"thru{n}", "x0": min(p[0] for p in pts) - r, "y0": min(p[1] for p in pts) - r,
                    "x1": max(p[0] for p in pts) + r, "y1": max(p[1] for p in pts) + r})
    for n, h in enumerate(lay.get("headers", [])):
        (cx, cy, bl, bw), _ = _header_geom(h)
        out.append({"ref": f"header{n}", "x0": cx - bl / 2, "y0": cy - bw / 2, "x1": cx + bl / 2, "y1": cy + bw / 2})
    for b in lay.get("blocks", []):
        if b["z0"] <= _board(lay)[2] + 0.01:  # only blocks sitting on the board
            out.append({"ref": b["ref"], "x0": b["x"] - b["l"] / 2, "y0": b["y"] - b["w"] / 2,
                        "x1": b["x"] + b["l"] / 2, "y1": b["y"] + b["w"] / 2})
    for c in lay.get("cyls", []):
        if c["z0"] <= _board(lay)[2] + 0.01 and not c.get("bore_d"):  # hollow mounts may hold parts
            r = c["d"] / 2
            out.append({"ref": c["ref"], "x0": c["x"] - r, "y0": c["y"] - r, "x1": c["x"] + r, "y1": c["y"] + r})
    return out


def main(project):
    """Print expected values and write keepouts.json for layout_check."""
    lay = json.loads((project / "parameters" / "layout.json").read_text())
    (project / "parameters" / "keepouts.json").write_text(json.dumps(keepouts(lay), indent=1))
    vol, bbox, parts = expected(lay)
    print(json.dumps({"volume": vol, "bbox": bbox, "breakdown": parts}, indent=1))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    main(pathlib.Path(sys.argv[1]))
